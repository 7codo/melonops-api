from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from app.lib.db.database import create_db_and_tables
from app.lib.db.models import MCPModel
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from app.lib.ai.workflows.chat_workflow import chat_workflow
from app.lib.ai.workflows.agent_workflow import agent_workflow
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.lib.config import get_settings
import logging
import sys
import uvicorn
import os
from typing import List
from fastapi import HTTPException
from app.api.dependencies import (
    print_request_headers,
    set_checkpointer,
    get_checkpointer,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

origins = ["http://localhost:3000"]

settings = get_settings()
logging.warning(f"Current settings: {settings.model_dump()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url
    ) as checkpointer:
        logger.info("Setting up checkpointer...")
        await checkpointer.setup()

        # Set the checkpointer instance globally
        set_checkpointer(checkpointer)

        chat_graph = chat_workflow.compile(checkpointer=checkpointer)
        agent_graph = agent_workflow.compile(checkpointer=checkpointer)
        logger.info("Workflows compiled successfully")

        sdk = CopilotKitRemoteEndpoint(
            agents=[
                LangGraphAgent(
                    name="chat_agent",
                    description="",
                    graph=chat_graph,
                ),
                LangGraphAgent(
                    name="agent_agent",
                    description="",
                    graph=agent_graph,
                ),
            ],
        )

        add_fastapi_endpoint(app, sdk, "/copilotkit")
        logger.info("Initializing application...")
        create_db_and_tables()
        logger.info("Database and tables created successfully")
        logger.info("Application startup completed successfully")
        yield
        logger.info("Shutting down application...")


app = FastAPI(lifespan=lifespan, dependencies=[Depends(print_request_headers)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GetToolsRequest(BaseModel):
    mcps: List[MCPModel]
    user_id: str


@app.post("/get_tools")
async def get_tools(request: GetToolsRequest):
    """Get tools from MCPs."""
    try:
        tools = await get_tools_from_mcps(request.mcps, request.user_id)
        return [{"name": tool.name, "description": tool.description} for tool in tools]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
def health():
    """Health check."""
    logger.debug("Health check endpoint called")
    return {"status": "ok"}


@app.delete("/checkpointer/{thread_id}")
async def delete_checkpointer(
    thread_id: str, checkpointer: AsyncPostgresSaver = Depends(get_checkpointer)
):
    """Delete a checkpointer thread."""
    try:
        await checkpointer.adelete_thread(thread_id)
        logger.info(f"Successfully deleted checkpointer thread: {thread_id}")
        return {"message": f"Checkpointer thread {thread_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting checkpointer thread {thread_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete checkpointer thread: {str(e)}"
        )


# For dev env
def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api.main:app",  # the path to your FastAPI file, replace this if its different
        host="localhost",
        port=port,
        reload=True,  # Disable reload in production
    )


if __name__ == "__main__":
    main()

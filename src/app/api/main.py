import asyncio
from contextlib import asynccontextmanager
from app.api.streaming_handler import streaming_handler
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# from app.lib.ai.workflows.test_workflow import test_graph
from app.lib.db.database import create_db_and_tables
from app.lib.db.models import MCPModel
from app.lib.ai.workflows.test_workflow import test_workflow
from app.lib.config import get_settings
import logging
import sys
import uvicorn
import os


from typing import List
from fastapi import HTTPException
from app.api.dependencies import (
    get_checkpointer,
)

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
from fastapi.responses import StreamingResponse
import json
from typing import Dict, Any, AsyncGenerator
import sys

# ... (other imports and Windows event loop policy setup)

logger = logging.getLogger(__name__)
origins = ["http://localhost:3000"]
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application...")
    create_db_and_tables()

    # Initialize graph in memory
    logger.info("Initializing graph and checkpointer...")
    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url
    ) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        app.state.graph = test_workflow.compile()  # checkpointer=checkpointer
        logger.info("Application startup completed successfully")
        yield
        logger.info("Shutting down application...")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CopilotRequest(BaseModel):
    thread_id: str
    agent_id: str
    messages: list
    id: str


@app.post("/copilot")
async def copilotkit(request: Request):
    body = await request.json()
    thread_id = body["thread_id"]
    messages = body["messages"]

    # Get pre-initialized graph from app state
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    # Create streaming response with AI SDK protocol
    return StreamingResponse(
        streaming_handler(graph, {"messages": messages}, config),
        media_type="text/plain; charset=utf-8",
        headers={"x-vercel-ai-data-stream": "v1"},
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


@app.get("/healthy")
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
        "app.api.main:app",
        host="localhost",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()

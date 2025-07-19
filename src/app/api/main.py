import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel

from app.api.dependencies import (
    get_checkpointer,
    set_checkpointer,
    verify_session_token,
)
from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from app.lib.ai.workflows.agent_workflow import agent_workflow
from app.lib.ai.workflows.chat_workflow import chat_workflow
from app.lib.config import get_settings
from app.lib.db.database import create_db_and_tables

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


settings = get_settings()

origins = [settings.frontend_app_url]
logging.warning(f"Current settings: {settings.model_dump()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url
    ) as checkpointer:
        Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        langfuse = get_client()
        if langfuse.auth_check():
            logger.info("Langfuse client is authenticated and ready!")
        else:
            logger.info(
                "Authentication failed. Please check your credentials and host."
            )

        logger.info("Setting up checkpointer...")

        await checkpointer.setup()
        # Set the checkpointer instance globally
        set_checkpointer(checkpointer)
        langfuse_handler = CallbackHandler()

        chat_graph = chat_workflow.compile(checkpointer=checkpointer).with_config(
            {"callbacks": [langfuse_handler]}
        )
        agent_graph = agent_workflow.compile(checkpointer=checkpointer).with_config(
            {"callbacks": [langfuse_handler]}
        )

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
        # langfuse.shutdown()
        logger.info("Shutting down application...")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GetToolsRequest(BaseModel):
    mcps_ids: List[str]
    user_id: str


@app.post("/get_tools")
async def get_tools(
    request: GetToolsRequest,
    _=Depends(verify_session_token),
):
    """Get tools from MCPs."""
    try:
        tools = await get_tools_from_mcps(request.mcps_ids, request.user_id)
        return [{"name": tool.name, "description": tool.description} for tool in tools]
    except Exception as e:
        logger.error(f"Error in get_tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}")


class GetLLMUsageRequest(BaseModel):
    user_id: str
    llm: str


@app.post("/token_usage")
async def get_llm_usage(
    request: GetLLMUsageRequest,
    _=Depends(verify_session_token),
):
    """Get LLM token usage for a user and model."""
    try:
        from app.lib.usage_utils import get_llm_usage_for_active_subscription_range

        usage = get_llm_usage_for_active_subscription_range(
            request.user_id, request.llm
        )
        return usage
    except Exception as e:
        logger.error(f"Error in get_llm_usage: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get LLM usage: {str(e)}"
        )


@app.get("/health")
def health():
    """Health check."""
    logger.debug("Health check endpoint called")
    return {"status": "ok"}


class DeleteThreadsRequest(BaseModel):
    thread_ids: List[str]


@app.delete("/checkpointer/delete_threads")
async def delete_checkpointer(
    request: DeleteThreadsRequest = Body(...),
    checkpointer: AsyncPostgresSaver = Depends(get_checkpointer),
    _=Depends(verify_session_token),
):
    """Delete one or more checkpointer threads."""
    results = {"deleted": [], "failed": []}
    for thread_id in request.thread_ids:
        try:
            await checkpointer.adelete_thread(thread_id)
            logger.info(f"Successfully deleted checkpointer thread: {thread_id}")
            results["deleted"].append(thread_id)
        except Exception as e:
            logger.error(f"Error deleting checkpointer thread {thread_id}: {e}")
            results["failed"].append({"thread_id": thread_id, "error": str(e)})
    return results


# For dev env
def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.api.main:app",
        host="localhost",
        port=port,
    )


if __name__ == "__main__":
    main()

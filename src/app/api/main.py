from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.lib.db.database import create_db_and_tables
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from app.lib.ai.workflows.chat_workflow import chat_workflow
from app.lib.ai.workflows.agent_workflow import agent_workflow
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.lib.config import get_settings
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

origins = ["http://localhost:3000"]

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application...")
    create_db_and_tables()
    logger.info("Database and tables created successfully")

    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url
    ) as checkpointer:
        logger.info("Setting up checkpointer...")
        await checkpointer.setup()
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


@app.get("/health")
def health():
    """Health check."""
    logger.debug("Health check endpoint called")
    return {"status": "ok"}


# For dev env
# def main():
#     """Run the uvicorn server."""
#     port = int(os.getenv("PORT", "8000"))
#     uvicorn.run(
#         "app.api.main:app",  # the path to your FastAPI file, replace this if its different
#         host="localhost",
#         port=port,
#         reload=True,  # Disable reload in production
#     )


# if __name__ == "__main__":
#     main()

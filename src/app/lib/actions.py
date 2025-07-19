import logging
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlmodel import Session, select

from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from app.lib.caching_utils import async_cached_function, cached_function
from app.lib.config import get_settings
from app.lib.constants import (
    azure_api_version,
    support_google_models,
    support_models,
    support_openai_models,
)
from app.lib.db.database import engine
from app.lib.db.models import AgentMcpModel, AgentModel, SessionModel
from app.lib.usage_utils import check_allowed_model

settings = get_settings()

# Set up logger
logger = logging.getLogger(__name__)


@cached_function()
def get_right_model(
    *, llm: str, user_id: str
) -> AzureChatOpenAI | ChatGoogleGenerativeAI:
    check_allowed_model(llm=llm, user_id=user_id)
    if llm not in support_models:
        logger.error(f"Model '{llm}' is not supported for user_id={user_id}.")
        raise Exception(
            "The selected model is not supported. Please choose a different model or contact support for assistance."
        )
    if llm in support_openai_models:
        model = AzureChatOpenAI(
            api_key=SecretStr(settings.azure_api_key),
            azure_endpoint=settings.azure_endpoint,
            api_version=azure_api_version,
            azure_deployment=llm,
            name=llm,
            temperature=0.1,
        )
    elif llm in support_google_models:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=settings.google_api_key
        )
    else:
        logger.error(f"Model type for '{llm}' is not recognized for user_id={user_id}.")
        raise Exception(
            "The specified model type is not recognized. Please check the model configuration or contact support for guidance."
        )
    logger.info(f"Returning model instance for llm='{llm}', user_id={user_id}.")
    return model


@async_cached_function()
async def generate_tools(*, agent_id: str, user_id: str, tools_ids: list[str]):
    """
    Retrieve agent data and associated tools for a given agent and user.

    Args:
        agent_id (str): The ID of the agent.
        user_id (str): The ID of the user.

    Returns:
        dict: A dictionary containing agent data and a list of tools.
    """
    with Session(engine) as session:
        # Fetch related MCPs
        agent_mcp_links = list(
            session.exec(
                select(AgentMcpModel).where(AgentMcpModel.agent_id == agent_id)
            )
        )
        mcp_ids: list[str] = [str(link.mcp_id) for link in agent_mcp_links]

        tools = []
        if mcp_ids:
            # Generate tools from MCPs
            all_tools = await get_tools_from_mcps(mcp_ids, user_id)
            # Filter tools based on tools_ids if provided
            if tools_ids and len(tools_ids) > 0:
                tools = [tool for tool in all_tools if tool.name in tools_ids]
            else:
                tools = all_tools

        # Prepare enhanced agent data dictionary
        logger.info(f"Returning tools for agent_id={agent_id}, user_id={user_id}.")
        return tools


@async_cached_function()
async def get_agent(agent_id: str) -> AgentModel:
    with Session(engine) as session:
        agent_data = session.exec(
            select(AgentModel).where(AgentModel.id == agent_id)
        ).first()

        if not agent_data:
            logger.error(f"No agent found with ID {agent_id}.")
            raise ValueError(
                f"No agent was found with ID {agent_id}. Please verify the ID and try again."
            )
        logger.info(f"Returning agent data for agent_id={agent_id}.")
        return agent_data


@async_cached_function()
async def verify_token(token: str):
    with Session(engine) as session:
        statement = select(SessionModel).where(SessionModel.token == token)
        try:
            session_from_db = session.exec(statement).one()
        except (NoResultFound, MultipleResultsFound):
            logger.error(
                f"Session not found or multiple sessions found for token={token}."
            )
            raise Exception(
                "The session is invalid. Please try again or initiate a new session."
            )

        now = datetime.now()
        if now > session_from_db.expires_at:
            logger.error(f"Session expired for token={token}.")
            raise Exception(
                "Your session has expired. Please log in again to continue."
            )

        logger.info(f"Returning session for token={token}.")
        return session_from_db

from uuid import UUID

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr
from sqlmodel import Session, select

from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from app.lib.config import get_settings
from app.lib.constants import (
    support_google_models,
    support_models,
    support_openai_models,
)
from app.lib.db.database import engine
from app.lib.db.models import AgentMcpModel, AgentModel, MCPModel

settings = get_settings()


def get_right_model(llm: str) -> AzureChatOpenAI | ChatGoogleGenerativeAI:
    if llm not in support_models:
        raise Exception("This model is not supported")
    if llm in support_openai_models:
        model = AzureChatOpenAI(
            api_key=SecretStr(settings.azure_api_key),
            azure_endpoint=settings.azure_endpoint,
            api_version="2025-01-01-preview",
            azure_deployment="gpt-4.1-mini",
            temperature=0.1,
        )
    elif llm in support_google_models:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", google_api_key=settings.google_api_key
        )
    else:
        raise Exception("Unknown model type")
    return model


async def generate_agent_data(*, agent_id: str, user_id: str) -> dict:
    """
    Retrieve agent data and associated tools for a given agent and user.

    Args:
        agent_id (str): The ID of the agent.
        user_id (str): The ID of the user.

    Returns:
        dict: A dictionary containing agent data and a list of tools.
    """
    with Session(engine) as session:
        agent_data = session.exec(
            select(AgentModel).where(AgentModel.id == agent_id)
        ).first()

        if not agent_data:
            raise ValueError(f"Agent with id {agent_id} not found")

        # Fetch related MCPs
        agent_mcp_links = list(
            session.exec(
                select(AgentMcpModel).where(AgentMcpModel.agent_id == agent_id)
            )
        )
        mcp_ids: list[UUID] = [link.mcp_id for link in agent_mcp_links]

        tools = []
        if mcp_ids:
            statement = select(MCPModel).where(MCPModel.id.in_(mcp_ids))  # type: ignore
            mcps = list(session.exec(statement).all())
            # Generate tools from MCPs
            tools = await get_tools_from_mcps(mcps, user_id)

        # Prepare enhanced agent data dictionary
        agent_info = {
            "id": str(agent_data.id),
            "name": getattr(agent_data, "name", None),
            "system_prompt": getattr(agent_data, "system_prompt", None),
            "tools": tools,
        }
        return agent_info

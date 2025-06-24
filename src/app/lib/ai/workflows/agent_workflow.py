from uuid import UUID
from copilotkit import CopilotKitState
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from sqlmodel import Session, select
from app.lib.db.models import AgentModel, MCPModel, AgentMcpModel
from app.lib.db.database import engine
from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from app.lib.config import get_settings
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentState(CopilotKitState):
    pass


model = AzureAIChatCompletionsModel(
    credential=settings.azure_inference_credential,
    endpoint=settings.azure_inference_endpoint,
    api_version="2024-12-01-preview",
    model="gpt-4.1-mini",
)


async def agent_node(state: AgentState, config: RunnableConfig):
    print("AGENT TRIGGER")
    configurable = config.get("configurable", {})
    # llm = configurable.get("llm", "google_genai:gemini-2.0-flash")
    userId = configurable.get("user_id")
    agentId = configurable.get("agent_id")

    if not userId:
        raise ValueError("user_id is required in config")
    if not agentId:
        raise ValueError("agent_id is required in config")

    # Fetch agent
    with Session(engine) as session:
        agent = session.exec(select(AgentModel).where(AgentModel.id == agentId)).first()

        if not agent:
            raise ValueError(f"Agent with id {agentId} not found")
        # Fetch related MCPs
        agent_mcp_links = list(
            session.exec(select(AgentMcpModel).where(AgentMcpModel.agent_id == agentId))
        )

        mcp_ids: list[UUID] = [link.mcp_id for link in agent_mcp_links]

        tools = []
        if mcp_ids:  # Only query MCPs if there are IDs
            statement = select(MCPModel).where(MCPModel.id.in_(mcp_ids))  # type: ignore
            mcps = list(session.exec(statement).all())

            # Generate tools from MCPs
            tools = await get_tools_from_mcps(mcps, userId)

    # Pass tools, name, and system_prompt to create_react_agent

    agent = create_react_agent(
        model, tools, name=agent.name, prompt=agent.system_prompt
    )

    response = await agent.ainvoke({"messages": state["messages"]}, config)

    return {
        "messages": response["messages"],
    }


agent_workflow = StateGraph(AgentState)
agent_workflow.add_node("simple", agent_node)

agent_workflow.set_entry_point("simple")
agent_workflow.add_edge("simple", END)


async def run(user_input: str):
    """
    Run the workflow with user input.

    Args:
        user_input (str): The user's input message

    Returns:
        str: The AI's response
    """
    messages = [HumanMessage(content=user_input)]

    graph = agent_workflow.compile()

    response = await graph.ainvoke(
        {"messages": messages},
        {
            "configurable": {
                "user_id": "XViAlHlCmlCDcQL8qGz7a5JhMAIMsqcu",
                "agent_id": "64d60d70-ae87-4be2-978f-79f6ea43adf1",
            }
        },
    )
    print("response", response)


# Example usage:
if __name__ == "__main__":
    asyncio.run(run("What can you do?"))

from uuid import UUID
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import create_react_agent
from sqlmodel import Session, select
from app.lib.db.models import AgentModel, MCPModel, AgentMcpModel
from app.lib.db.database import engine
from app.lib.ai.tools.mcp_tools import get_tools_from_mcps
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from app.lib.config import get_settings
from langchain_core.tools import tool
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


@tool
def check_weather(location: str) -> str:
    """Return the weather forecast for the specified location."""
    return f"It's always sunny in {location}"


class AgentState(MessagesState):
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

    # if not userId:
    #     raise ValueError("user_id is required in config")
    # if not agentId:
    #     raise ValueError("agent_id is required in config")

    # # Fetch agent
    # with Session(engine) as session:
    #     agent_data = session.exec(
    #         select(AgentModel).where(AgentModel.id == agentId)
    #     ).first()

    #     if not agent_data:
    #         raise ValueError(f"Agent with id {agentId} not found")
    #     # Fetch related MCPs
    #     agent_mcp_links = list(
    #         session.exec(select(AgentMcpModel).where(AgentMcpModel.agent_id == agentId))
    #     )

    #     mcp_ids: list[UUID] = [link.mcp_id for link in agent_mcp_links]

    #     tools = []
    #     if mcp_ids:  # Only query MCPs if there are IDs
    #         statement = select(MCPModel).where(MCPModel.id.in_(mcp_ids))  # type: ignore
    #         mcps = list(session.exec(statement).all())

    #         # Generate tools from MCPs
    #         tools = await get_tools_from_mcps(mcps, userId)

    # Pass tools, name, and system_prompt to create_react_agent

    print(f"\n\nstate messages: {state['messages']}\n\n")
    agent = create_react_agent(
        model,
        tools=[check_weather],
    )
    print("\n\nAfter create the agent\n\n")
    # what are google sheets I have
    response = agent.invoke(
        {"messages": [HumanMessage("check the weather in Algeria")]}, config
    )
    print(f"\n\response messages: {response['messages']}\n\n")
    # Extract only the new messages that were added in this step
    # The response contains all messages, but we only want the new ones
    # formatted_response = []
    # for msg in response["messages"]:
    #     if isinstance(msg, ToolMessage):
    #         print(f"pass: {msg}")
    #         pass
    #     formatted_response.append(msg)

    # print(f"\n\nresponse messages: {state["messages"]}\n\n")

    return {
        "messages": [AIMessage("No problem")],
    }


agent_workflow = StateGraph(AgentState)
agent_workflow.add_node("agent", agent_node)

agent_workflow.set_entry_point("agent")
agent_workflow.add_edge("agent", END)


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
    asyncio.run(run("what are google sheets I have"))

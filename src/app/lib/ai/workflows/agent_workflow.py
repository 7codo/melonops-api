import asyncio
import logging
import sys

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import create_react_agent

from app.lib.actions import generate_agent_data, get_right_model
from app.lib.config import get_settings
from app.lib.constants import default_model

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


async def agent_node(state: AgentState, config: RunnableConfig):
    print("AGENT TRIGGER")
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", default_model)
    user_id = configurable.get("user_id", None)
    agent_id = configurable.get("agent_id", None)

    if not user_id:
        raise ValueError("user_id is required in config")
    if not agent_id:
        raise ValueError("agent_id is required in config")

    model = get_right_model(llm)
    agent_data = await generate_agent_data(agent_id=agent_id, user_id=user_id)

    agent = create_react_agent(
        model,
        tools=agent_data["tools"],
        name=agent_data["name"],
        prompt=agent_data["system_prompt"],
    )
    response = agent.invoke({"messages": state["messages"]}, config)

    return {
        "messages": response["messages"],
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

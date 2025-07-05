import logging
import sys

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from app.lib.actions import generate_tools, get_agent, get_right_model
from app.lib.config import get_settings

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


class AgentState(CopilotKitState):
    user_id: str | None
    agent_id: str | None
    llm: str | None
    name: str | None
    system_prompt: str | None


async def agent_node(state: AgentState, config: RunnableConfig):
    try:
        configurable = config.get("configurable", {})
        llm = configurable.get("llm", None)
        user_id = configurable.get("user_id", None)
        agent_id = configurable.get("agent_id", None)

        llm_state = state.get("llm")
        if llm is not None and llm_state is None:
            llm_state = llm

        if llm_state is None:
            raise ValueError("LLM value is required!")

        model = get_right_model(llm_state)

        agent_id_state = state.get("agent_id")
        if agent_id_state is None and agent_id is not None:
            agent_id_state = agent_id

        if agent_id_state is None:
            raise ValueError("Agent ID is required!")

        user_id_state = state.get("user_id")
        if user_id_state is None and user_id is not None:
            user_id_state = user_id

        if user_id_state is None:
            raise ValueError("User ID is required!")
        name_state = state.get("name")
        system_prompt_state = state.get("system_prompt")
        if name_state is None or system_prompt_state is None:
            agent_data = await get_agent(agent_id_state)
            system_prompt_state = agent_data.system_prompt
            name_state = agent_data.name

        tools = await generate_tools(agent_id=agent_id_state, user_id=user_id_state)

        sanitized_name = name_state.replace(" ", "_") if name_state else "agent"

        agent = create_react_agent(
            model,
            tools=tools,
            name=sanitized_name,
            prompt=system_prompt_state,
        )
        response = await agent.ainvoke({"messages": state["messages"]}, config)

        return {
            "messages": response["messages"],
            "user_id": user_id,
            "agent_id": agent_id,
            "llm": llm_state,
            "name": name_state,
            "system_prompt": system_prompt_state,
        }
    except ValueError as e:
        logger.error(f"Validation error in agent_node: {e}")
        messages = state["messages"].append(AIMessage(f"Error: {str(e)}"))
        return {
            "messages": messages,
            "user_id": user_id,
            "agent_id": agent_id,
            "llm": llm_state if "llm_state" in locals() else None,
            "name": name_state if "name_state" in locals() else None,
            "system_prompt": system_prompt_state
            if "system_prompt_state" in locals()
            else None,
        }
    except Exception as e:
        logger.error(f"Unexpected error in agent_node: {e}", exc_info=True)
        messages = state["messages"].append(
            AIMessage("An unexpected error occurred. Please try again.")
        )
        return {
            "messages": messages,
            "user_id": user_id,
            "agent_id": agent_id,
            "llm": llm_state if "llm_state" in locals() else None,
            "name": name_state if "name_state" in locals() else None,
            "system_prompt": system_prompt_state
            if "system_prompt_state" in locals()
            else None,
        }


agent_workflow = StateGraph(AgentState)
agent_workflow.add_node("agent", agent_node)

agent_workflow.set_entry_point("agent")
agent_workflow.add_edge("agent", END)

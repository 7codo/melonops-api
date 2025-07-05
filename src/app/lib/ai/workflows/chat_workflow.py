import logging
import sys

from copilotkit import CopilotKitState
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.lib.actions import get_agent, get_right_model
from app.lib.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

settings = get_settings()


class State(CopilotKitState):
    system_message: str | None
    llm: str | None


async def chat_node(state: State, config: RunnableConfig):
    try:
        configurable = config.get("configurable", {})
        llm = configurable.get("llm", None)
        agent_id = configurable.get("agent_id", None)

        system_prompt_state = state.get("system_message")

        if system_prompt_state is None and agent_id is not None:
            agent = await get_agent(agent_id)
            system_prompt_state = agent.system_prompt

        messages = state["messages"]
        if system_prompt_state:
            messages = [SystemMessage(content=system_prompt_state)] + messages
        llm_state = state.get("llm")
        if llm is not None and llm_state is None:
            llm_state = llm

        if llm_state is None:
            raise ValueError("LLM value is required!")

        model = get_right_model(llm_state)
        response = await model.ainvoke(messages)
        return {
            "messages": [response],
            "system_message": system_prompt_state,
            "llm": llm_state,
        }
    except ValueError as e:
        logger.error(f"Validation error in agent_node: {e}")
        messages = state["messages"].append(AIMessage(f"Error: {str(e)}"))
        return {
            "messages": messages,
            "llm": llm_state if "llm_state" in locals() else None,
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
            "llm": llm_state if "llm_state" in locals() else None,
            "system_prompt": system_prompt_state
            if "system_prompt_state" in locals()
            else None,
        }


chat_workflow = StateGraph(State)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("chat")
chat_workflow.add_edge("chat", END)
checkpointer = MemorySaver()
chat_graph = chat_workflow.compile(checkpointer=checkpointer)

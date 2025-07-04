import logging
import sys

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from app.lib.actions import get_agent, get_right_model
from app.lib.config import get_settings
from app.lib.constants import default_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

settings = get_settings()


class State(MessagesState):
    pass


async def chat_node(state: State, config: RunnableConfig):
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", default_model)
    user_id = configurable.get("user_id", None)
    agent_id = configurable.get("agent_id", None)

    if not user_id:
        raise ValueError("user_id is required in config")
    if not agent_id:
        raise ValueError("agent_id is required in config")

    # TODO: Implement get_agent function or import it
    messages = state["messages"]

    # Check if the last message is not a SystemMessage
    if not isinstance(messages[-1], SystemMessage):
        agent = await get_agent(agent_id)
        if agent.system_prompt:
            messages = [SystemMessage(content=agent.system_prompt)] + messages

    model = get_right_model(llm)
    response = await model.ainvoke(messages)
    return {
        "messages": [response],
    }


chat_workflow = StateGraph(State)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("chat")
chat_workflow.add_edge("chat", END)
checkpointer = MemorySaver()
chat_graph = chat_workflow.compile(checkpointer=checkpointer)

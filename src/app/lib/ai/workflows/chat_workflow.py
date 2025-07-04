import logging
import sys

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from app.lib.actions import get_right_model
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


def chat_node(state: State, config: RunnableConfig):
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", default_model)
    messages = state["messages"]
    model = get_right_model(llm)
    response = model.invoke(messages)
    return {
        "messages": [response],
    }


chat_workflow = StateGraph(State)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("chat")
chat_workflow.add_edge("chat", END)
checkpointer = MemorySaver()
chat_graph = chat_workflow.compile(checkpointer=checkpointer)

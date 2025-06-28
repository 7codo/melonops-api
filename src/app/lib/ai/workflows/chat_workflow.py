import logging
import sys

from app.lib.config import get_settings
from copilotkit import CopilotKitState
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

settings = get_settings()

model = AzureAIChatCompletionsModel(
    credential=settings.azure_inference_credential,
    endpoint=settings.azure_inference_endpoint,
    api_version="2024-12-01-preview",
    model="gpt-4.1-mini",
)


class State(CopilotKitState):
    pass


def chat_node(state: State, config: RunnableConfig):
    messages = state["messages"]
    response = model.invoke(messages)
    return {
        "messages": [response],
    }


chat_workflow = StateGraph(State)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("chat")
chat_workflow.add_edge("chat", END)

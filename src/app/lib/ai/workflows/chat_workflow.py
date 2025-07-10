import logging
import sys

from copilotkit import CopilotKitState
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.lib.actions import get_agent, get_right_model, verify_token
from app.lib.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

settings = get_settings()


class InputState(CopilotKitState):
    pass


class OutputState(CopilotKitState):
    pass


class OverallState(InputState, OutputState):
    system_message: str | None
    llm: str | None
    user_id: str | None
    auth_token: str | None


async def chat_node(state: OverallState, config: RunnableConfig):
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", None)
    agent_id = configurable.get("agent_id", None)
    user_id = configurable.get("user_id", None)
    auth_token = configurable.get("auth_token", None)

    auth_token_state = state.get("auth_token")
    if auth_token is not None and auth_token_state is None:
        auth_token_state = auth_token

    if auth_token_state is None:
        raise ValueError("auth_token value is required!")

    await verify_token(auth_token_state)

    system_prompt_state = state.get("system_message")

    if system_prompt_state is None and agent_id is not None:
        agent = await get_agent(agent_id)
        system_prompt_state = agent.system_prompt

    messages = state["messages"]
    if system_prompt_state:
        messages = [SystemMessage(content=system_prompt_state)] + messages
    llm_state = state.get("llm")
    user_id_state = state.get("user_id")
    if llm is not None and llm_state is None:
        llm_state = llm
    if user_id is not None and user_id_state is None:
        user_id_state = user_id

    if llm_state is None:
        raise ValueError("LLM value is required!")
    if user_id_state is None:
        raise ValueError("user_id value is required!")

    model = get_right_model(llm=llm_state, user_id=user_id_state)
    response = await model.ainvoke(messages)
    return {
        "messages": [response],
        "system_message": system_prompt_state,
        "llm": llm_state,
        "user_id": user_id_state,
        "auth_token": auth_token_state,
    }


chat_workflow = StateGraph(OverallState, input=InputState, output=OutputState)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("chat")
chat_workflow.add_edge("chat", END)
checkpointer = MemorySaver()
chat_graph = chat_workflow.compile(checkpointer=checkpointer)


# async def test_chat_graph():
#     """Test chat_graph with a sample input."""

#     response = await chat_graph.ainvoke(
#         {"messages": [HumanMessage("Hi")]},  # first positional argument: input
#         {
#             "configurable": {
#                 "user_id": "XViAlHlCmlCDcQL8qGz7a5JhMAIMsqcu",
#                 "agent_id": "64d60d70-ae87-4be2-978f-79f6ea43adf1",
#                 "llm": "gpt-4.1-mini",
#                 "thread_id": "5454",
#                 "auth_token": "test_auth_token",
#             }
#         },  # second positional argument: RunnableConfig
#     )
#     print(response)


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(test_chat_graph())

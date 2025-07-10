import logging
import sys

from copilotkit import CopilotKitState
from langchain_core.runnables import RunnableConfig
from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from app.lib.actions import generate_tools, get_agent, get_right_model, verify_token
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
    user_id: str | None
    agent_id: str | None
    llm: str | None
    name: str | None
    system_prompt: str | None
    auth_token: str | None
    session_id: str | None


@observe()
async def process_agent_query(
    *,
    messages,
    user_id,
    session_id,
    llm,
    agent_id,
    name,
    system_prompt,
):
    langfuse = get_client()
    langfuse.update_current_trace(
        name="agent_workflow",
        session_id=session_id,
        user_id=user_id,
        tags=[agent_id],
        input={"messages": messages},
    )
    langfuse_handler = CallbackHandler()
    model = get_right_model(llm=llm, user_id=user_id)
    tools = await generate_tools(agent_id=agent_id, user_id=user_id)
    sanitized_name = name.replace(" ", "_") if name else "agent"
    agent = create_react_agent(
        model,
        tools=tools,
        name=sanitized_name,
        prompt=system_prompt,
    )
    response = await agent.ainvoke(
        {"messages": messages},
        config={"callbacks": [langfuse_handler]},
    )
    langfuse.update_current_trace(output={"response": response["messages"]})
    return response["messages"]


async def agent_node(state: OverallState, config: RunnableConfig):
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", None)
    user_id = configurable.get("user_id", None)
    agent_id = configurable.get("agent_id", None)
    session_id = configurable.get("session_id", None)
    auth_token = configurable.get("auth_token", None)

    auth_token_state = state.get("auth_token")
    if auth_token is not None and auth_token_state is None:
        auth_token_state = auth_token
    if auth_token_state is None:
        raise ValueError("auth_token value is required!")
    await verify_token(auth_token_state)

    agent_id_state = state.get("agent_id")
    if agent_id is not None and agent_id_state is None:
        agent_id_state = agent_id
    if agent_id_state is None:
        raise ValueError("Agent ID is required!")

    user_id_state = state.get("user_id")
    if user_id is not None and user_id_state is None:
        user_id_state = user_id
    session_id_state = state.get("session_id")
    if session_id is not None and session_id_state is None:
        session_id_state = session_id
    if user_id_state is None:
        raise ValueError("User ID is required!")
    if session_id_state is None:
        raise ValueError("session_id value is required!")

    llm_state = state.get("llm")
    if llm is not None and llm_state is None:
        llm_state = llm
    if llm_state is None:
        raise ValueError("LLM value is required!")

    name_state = state.get("name")
    system_prompt_state = state.get("system_prompt")
    if name_state is None or system_prompt_state is None:
        agent_data = await get_agent(agent_id_state)
        system_prompt_state = agent_data.system_prompt
        name_state = agent_data.name

    messages = state["messages"]

    response_messages = await process_agent_query(
        messages=messages,
        user_id=user_id_state,
        session_id=session_id_state,
        llm=llm_state,
        agent_id=agent_id_state,
        name=name_state,
        system_prompt=system_prompt_state,
    )

    return {
        "messages": response_messages,
        "user_id": user_id_state,
        "agent_id": agent_id_state,
        "llm": llm_state,
        "name": name_state,
        "system_prompt": system_prompt_state,
        "auth_token": auth_token_state,
        "session_id": session_id_state,
    }


agent_workflow = StateGraph(OverallState, input=InputState, output=OutputState)
agent_workflow.add_node("agent", agent_node)

agent_workflow.set_entry_point("agent")
agent_workflow.add_edge("agent", END)

import logging

from copilotkit import CopilotKitState
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from app.lib.actions import generate_tools, get_agent, get_right_model, verify_token
from app.lib.config import get_settings
from app.lib.usage_utils import check_llm_token_limit, check_usage_limit

logger = logging.getLogger(__name__)
settings = get_settings()


class InputState(CopilotKitState):
    pass


class OutputState(CopilotKitState):
    llm: str | None
    error: str | None


class OverallState(InputState, OutputState):
    user_id: str | None
    agent_id: str | None
    name: str | None
    system_prompt: str | None
    auth_token: str | None
    session_id: str | None
    tools_ids: list[str] | None


async def verification_node(state: OverallState, config: RunnableConfig):
    configurable = config.get("configurable", {})
    llm = configurable.get("llm", None)
    user_id = configurable.get("user_id", None)
    agent_id = configurable.get("agent_id", None)
    session_id = configurable.get("session_id", None)
    auth_token = configurable.get("auth_token", None)

    agent_id_state = state.get("agent_id", None)
    auth_token_state = state.get("auth_token", None)
    messages = state.get("messages", [])
    llm_state = state.get("llm", None)
    user_id_state = state.get("user_id", None)
    name_state = state.get("name", None)
    system_prompt_state = state.get("system_prompt", None)
    session_id_state = state.get("session_id", None)
    tools_ids_state = state.get("tools_ids", None)

    try:
        if auth_token is not None and auth_token_state is None:
            auth_token_state = auth_token
        if auth_token_state is None:
            raise ValueError("auth_token value is required!")
        await verify_token(auth_token_state)

        if llm is not None and llm_state is None:
            llm_state = llm
        if user_id is not None and user_id_state is None:
            user_id_state = user_id

        if llm_state is None:
            raise ValueError("LLM value is required!")
        if user_id_state is None:
            raise ValueError("user_id value is required!")

        check_llm_token_limit(user_id=user_id_state, llm=llm_state)
        check_usage_limit(user_id=user_id_state)

        if agent_id is not None and agent_id_state is None:
            agent_id_state = agent_id
        if agent_id_state is None:
            raise ValueError("Agent ID is required!")

        if session_id is not None and session_id_state is None:
            session_id_state = session_id
        if session_id_state is None:
            raise ValueError("session_id value is required!")

        if name_state is None or system_prompt_state is None or tools_ids_state is None:
            agent_data = await get_agent(agent_id_state)
            name_state = agent_data.name
            if name_state is not None and name_state != "Untitled Agent":
                system_prompt_state = (
                    f"Your name is {name_state}, {agent_data.system_prompt}"
                )
            else:
                system_prompt_state = agent_data.system_prompt
            tools_ids_state = agent_data.tools_ids or []

        return {
            "error": None,
            "messages": messages,
            "user_id": user_id_state,
            "agent_id": agent_id_state,
            "llm": llm_state,
            "name": name_state,
            "system_prompt": system_prompt_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "tools_ids": tools_ids_state,
        }
    except Exception as e:
        logger.error(f"Error in agent_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "messages": messages,
            "user_id": user_id_state,
            "agent_id": agent_id_state,
            "llm": llm_state,
            "name": name_state,
            "system_prompt": system_prompt_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "tools_ids": tools_ids_state,
        }


async def agent_node(state: OverallState, config: RunnableConfig):
    llm_state = state.get("llm")
    user_id_state = state.get("user_id")
    auth_token_state = state.get("auth_token")
    session_id_state = state.get("session_id")
    agent_id_state = state.get("agent_id")
    tools_ids_state = state.get("tools_ids")
    system_prompt_state = state.get("system_message")
    name_state = state.get("name")

    messages = state["messages"]
    try:
        model = get_right_model(llm=llm_state, user_id=user_id_state)
        tools = await generate_tools(
            agent_id=agent_id_state, user_id=user_id_state, tools_ids=tools_ids_state
        )
        sanitized_name = name_state.replace(" ", "_") if name_state else "agent"
        agent = create_react_agent(
            model,
            tools=tools,
            name=sanitized_name,
            prompt=system_prompt_state,
        )
        response = await agent.ainvoke({"messages": messages}, config)
        messages = response["messages"]
        return {
            "error": None,
            "messages": messages,
            "user_id": user_id_state,
            "agent_id": agent_id_state,
            "llm": llm_state,
            "name": name_state,
            "system_prompt": system_prompt_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "tools_ids": tools_ids_state,
        }
    except Exception as e:
        logger.error(f"Error in agent_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "messages": messages,
            "user_id": user_id_state,
            "agent_id": agent_id_state,
            "llm": llm_state,
            "name": name_state,
            "system_prompt": system_prompt_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "tools_ids": tools_ids_state,
        }


def error_router(state: OverallState):
    if state.get("error"):
        return END
    return "agent"


agent_workflow = StateGraph(OverallState, input=InputState, output=OutputState)
agent_workflow.add_node("verification", verification_node)
agent_workflow.add_node("agent", agent_node)

agent_workflow.set_entry_point("verification")
agent_workflow.add_conditional_edges(
    "verification",
    error_router,
    [END, "agent"],
)
agent_workflow.add_edge("agent", END)

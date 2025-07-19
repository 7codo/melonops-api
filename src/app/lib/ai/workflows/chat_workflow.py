import logging

from copilotkit import CopilotKitState
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.lib.actions import get_agent, get_right_model, verify_token
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
    system_message: str | None
    auth_token: str | None
    agent_id: str | None
    session_id: str | None
    user_id: str | None


async def verification_node(state: OverallState, config: RunnableConfig):
    messages = state.get("messages", [])
    system_prompt_state = state.get("system_message", None)
    llm_state = state.get("llm", None)
    user_id_state = state.get("user_id", None)
    auth_token_state = state.get("auth_token", None)
    session_id_state = state.get("session_id", None)
    agent_id_state = state.get("agent_id", None)
    try:
        configurable = config.get("configurable", {})

        llm = configurable.get("llm", None)
        agent_id = configurable.get("agent_id", None)
        user_id = configurable.get("user_id", None)
        auth_token = configurable.get("auth_token", None)
        session_id = configurable.get("session_id", None)

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

        if system_prompt_state is None and agent_id is not None:
            agent = await get_agent(agent_id)
            if agent.name is not None and agent.name != "Untitled Agent":
                system_prompt_state = (
                    f"Your name is {agent.name}, {agent.system_prompt}"
                )
            else:
                system_prompt_state = agent.system_prompt

        if session_id is not None and session_id_state is None:
            session_id_state = session_id
        if agent_id is not None and agent_id_state is None:
            agent_id_state = agent_id

        if session_id_state is None:
            raise ValueError("session_id value is required!")
        if agent_id_state is None:
            raise ValueError("agent_id value is required!")

        return {
            "error": None,
            "messages": messages,
            "system_message": system_prompt_state,
            "llm": llm_state,
            "user_id": user_id_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "agent_id": agent_id_state,
        }
    except Exception as e:
        logger.error(f"Error in verification_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "messages": messages,
            "system_message": system_prompt_state,
            "llm": llm_state,
            "user_id": user_id_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "agent_id": agent_id_state,
        }


async def chat_node(state: OverallState, config: RunnableConfig):
    messages = state.get("messages", [])
    system_prompt_state = state.get("system_message", None)
    llm_state = state.get("llm", None)
    user_id_state = state.get("user_id", None)
    auth_token_state = state.get("auth_token", None)
    session_id_state = state.get("session_id", None)
    agent_id_state = state.get("agent_id", None)
    try:
        model = get_right_model(llm=llm_state, user_id=user_id_state)
        if system_prompt_state and not isinstance(messages[0], SystemMessage):
            updated_messages = [SystemMessage(content=system_prompt_state), *messages]
            messages = updated_messages

        response = await model.ainvoke(messages, config)

        return {
            "error": None,
            "messages": [response],
            "system_message": system_prompt_state,
            "llm": llm_state,
            "user_id": user_id_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "agent_id": agent_id_state,
        }

    except Exception as e:
        logger.error(f"Error in chat_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "messages": messages,
            "system_message": system_prompt_state,
            "llm": llm_state,
            "user_id": user_id_state,
            "auth_token": auth_token_state,
            "session_id": session_id_state,
            "agent_id": agent_id_state,
        }


def error_router(state: OverallState):
    if state.get("error"):
        return END
    return "chat"


chat_workflow = StateGraph(OverallState, input=InputState, output=OutputState)
chat_workflow.add_node("verification", verification_node)
chat_workflow.add_node("chat", chat_node)

chat_workflow.set_entry_point("verification")
chat_workflow.add_conditional_edges(
    "verification",
    error_router,
    [END, "chat"],
)
chat_workflow.add_edge("chat", END)

from langgraph.prebuilt import create_react_agent
from langgraph.graph import START, MessagesState, StateGraph, END
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from app.lib.config import get_settings
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.postgres import PostgresSaver
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from app.lib.config import get_settings

settings = get_settings()

# Add this import

settings = get_settings()

model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", google_api_key=settings.google_api_key
)


def get_weather(city: str) -> str:
    """Return the weather forecast for the specified location."""
    return f"Weather in {city}: sunny"


class WorkflowState(MessagesState):
    pass


def react_node(state: WorkflowState):
    react_agent = create_react_agent(
        model=model,
        tools=[get_weather],
        prompt="You are a helpful assistant",
    )
    result = react_agent.invoke({"messages": state["messages"]})

    return {"messages": result["messages"]}


test_workflow = StateGraph(WorkflowState)
test_workflow.add_node("react_node", react_node)
test_workflow.add_edge(START, "react_node")
test_workflow.add_edge("react_node", END)


# async def run_test_workflow(user_input: str):
#     """
#     Run the test workflow with user input.

#     Args:
#         user_input (str): The user's input message
#         checkpointer: Optional checkpointer for persistence (e.g., AsyncPostgresSaver)

#     Returns:
#         dict: The workflow's response
#     """
#     messages = [HumanMessage(content=user_input)]
#     print("settings.database_url", settings.database_url)
#     async with AsyncPostgresSaver.from_conn_string(
#         settings.database_url
#     ) as checkpointer:
#         await checkpointer.setup()
#         graph = test_workflow.compile(checkpointer=checkpointer)
#         response = await graph.ainvoke(
#             {"messages": messages},
#             {"configurable": {"thread_id": "123"}},  # 56123
#         )
#         print(response)
#     return response


# # Example usage for manual testing
# if __name__ == "__main__":
#     import sys

#     if sys.platform.startswith("win"):
#         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#     asyncio.run(run("What is the weather in Paris?"))

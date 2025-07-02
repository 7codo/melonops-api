import json
import logging
import uuid
from typing import Dict, Any, AsyncGenerator

from langchain_core.messages import AIMessage, ToolMessage


logger = logging.getLogger(__name__)


async def streaming_handler(
    graph: Any,
    input: Dict[str, Any],
    config: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    Generator that streams AI response using AI SDK data protocol
    """
    total_prompt_tokens = 0
    total_completion_tokens = 0
    message_id = None
    step_prompt_tokens = 0
    step_completion_tokens = 0
    step_started = False
    # Print input for debugging
    print(f"\n\n\ninput: {input}\n\n\n")

    try:
        async for item, metadata in graph.astream(
            input, config, stream_mode="messages"
        ):
            print(f"\n\n\nitem: {item}\n\n\n")
            print(f"metadata: {metadata}\n\n\n")

            # Get message id from item or generate one
            if not message_id:
                message_id = getattr(metadata, "thread_id", None) or str(uuid.uuid4())

            # Start step part (type f)
            if not step_started:
                yield f'f:{{"messageId":"{message_id}"}}\n'
                step_started = True

            # Update usage if available
            usage = getattr(item, "usage_metadata", None)
            if usage:
                step_prompt_tokens += usage.get("input_tokens", 0)
                step_completion_tokens += usage.get("output_tokens", 0)
                total_prompt_tokens += usage.get("input_tokens", 0)
                total_completion_tokens += usage.get("output_tokens", 0)

            # Stream content, tool calls, and tool results
            if hasattr(item, "content") and getattr(item, "content", None) != "":
                yield f"0:{json.dumps(item.content)}\n"
            if hasattr(item, "tool_calls") and getattr(item, "content", None) == "":
                for tool_call in item.tool_calls:
                    yield f"9:{json.dumps({'toolCallId': tool_call['id'], 'toolName': tool_call['name'], 'args': tool_call['args']})}\n"
            if isinstance(item, ToolMessage):
                yield f"a:{json.dumps({'toolCallId': item.id, 'result': item.content})}\n"

        # Finish step part (type e)
        yield (
            f'e:{{"finishReason":"stop","usage":{{"promptTokens":{step_prompt_tokens},"completionTokens":{step_completion_tokens}}},"isContinued":false}}\n'
        )

    except Exception as e:
        # Error part (type 3)
        yield f"3:{json.dumps(str(e))}\n"
        logger.error(f"Streaming error: {str(e)}")

    finally:
        # Final message completion (type d)
        yield f"d:{json.dumps({'finishReason': 'stop', 'usage': {'promptTokens': total_prompt_tokens, 'completionTokens': total_completion_tokens}})}\n"

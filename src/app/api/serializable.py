from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_core.messages import BaseMessage
from langchain_core.load import dumpd, load


class MessageAwareSerializer(JsonPlusSerializer):
    """Custom serializer that handles LangChain message objects"""

    def default(self, obj):
        # Convert LangChain messages to serializable dicts
        if isinstance(obj, BaseMessage):
            print(f"\n\n\n obj: {obj}")
            return dumpd(obj)
        # Handle other types normally
        return super()._default(obj)

    def loads(self, data: bytes):
        # First parse normally
        obj = super().loads(data)
        # Then recursively convert message dicts to objects
        return self._convert_messages(obj)

    def _convert_messages(self, obj):
        if isinstance(obj, dict):
            # Check if it's a serialized LangChain message
            if "lc" in obj and "id" in obj and obj["id"][0] == "langchain":
                try:
                    return load(obj)
                except Exception:
                    pass
            # Recurse into dictionaries
            return {k: self._convert_messages(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_messages(item) for item in obj]
        return obj

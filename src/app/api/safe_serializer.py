# serializers.py
import pickle
from typing import Any
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class SafeSerializer(JsonPlusSerializer):
    def dumps(self, obj: Any) -> bytes:
        try:
            return super().dumps(obj)
        except Exception as e:
            # Fallback to pickle for ANY error
            return pickle.dumps(obj)

    def loads(self, b: bytes) -> Any:
        try:
            return super().loads(b)
        except Exception:
            return pickle.loads(b)

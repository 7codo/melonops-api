import hashlib
import json
import time
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel

from app.lib.config import get_settings

settings = get_settings()

# Thread-safe cache storage
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = Lock()


def _generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """Generate cache key with safe parameter serialization"""

    def serialize(obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, BaseModel):
            return obj.dict()
        return obj

    args_ser = [serialize(a) for a in args]
    kwargs_ser = {k: serialize(v) for k, v in kwargs.items()}
    param_str = json.dumps([args_ser, sorted(kwargs_ser.items())], sort_keys=True)
    return f"{func_name}:{hashlib.sha256(param_str.encode()).hexdigest()}"


def _get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieve valid cache entry or None if expired/missing"""
    with _cache_lock:
        entry = _cache.get(cache_key)
        if not entry:
            return None

        # Check TTL expiration
        if entry.get("ttl") is not None:
            if time.time() - entry["cached_at"] > entry["ttl"]:
                del _cache[cache_key]
                return None
        return entry


def _cache_result(
    cache_key: str,
    result: Any,
    func_name: str,
    args: Tuple,
    kwargs: Dict,
    ttl: Optional[int] = None,
) -> None:
    """Store result in cache with metadata"""
    with _cache_lock:
        _cache[cache_key] = {
            "result": result,
            "func_name": func_name,
            "parameters": (args, kwargs),
            "cached_at": time.time(),
            "ttl": ttl,
        }


def invalidate_cache_by_parameter(
    func_name: str, param_name: str, param_value: Any
) -> None:
    """Invalidate cache entries for a specific function and parameter value"""
    with _cache_lock:
        keys_to_remove = []
        for key, entry in _cache.items():
            if entry["func_name"] != func_name:
                continue

            args, kwargs = entry["parameters"]
            # Check args (by position)
            if param_name.isdigit():
                pos = int(param_name)
                if pos < len(args) and args[pos] == param_value:
                    keys_to_remove.append(key)
            # Check kwargs
            elif param_name in kwargs and kwargs[param_name] == param_value:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del _cache[key]


def invalidate_cache_by_function(func_name: str) -> None:
    """Invalidate all cache entries for a specific function"""
    with _cache_lock:
        keys_to_remove = [k for k, v in _cache.items() if v["func_name"] == func_name]
        for key in keys_to_remove:
            del _cache[key]


def clear_all_cache() -> None:
    """Clear all cached results"""
    with _cache_lock:
        _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    with _cache_lock:
        return {
            "total_entries": len(_cache),
            "functions": list(set(v["func_name"] for v in _cache.values())),
        }


def cached_function(ttl: Optional[int] = None):
    """Decorator for synchronous functions with thread-safe caching"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            cache_key = _generate_cache_key(func_name, *args, **kwargs)

            # Check cache
            cached_data = _get_cached_data(cache_key)
            if cached_data:
                return cached_data["result"]

            # Compute and cache result
            result = func(*args, **kwargs)
            _cache_result(cache_key, result, func_name, args, kwargs, ttl)
            return result

        return wrapper

    return decorator


def async_cached_function(ttl: Optional[int] = None):
    """Decorator for asynchronous functions with thread-safe caching"""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            cache_key = _generate_cache_key(func_name, *args, **kwargs)

            # Check cache
            cached_data = _get_cached_data(cache_key)
            if cached_data:
                return cached_data["result"]

            # Compute and cache result
            result = await func(*args, **kwargs)
            _cache_result(cache_key, result, func_name, args, kwargs, ttl)
            return result

        return wrapper

    return decorator

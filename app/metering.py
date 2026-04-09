"""
Universal Agent Economy OS - Usage Metering

This module provides a Redis-ready usage metering store for v0.
It tracks total calls and total payment amounts per agent_id to lay the
groundwork for future billing and analytics. It uses Redis if REDIS_URL
is configured, otherwise it falls back to a thread-safe in-memory dictionary.
"""
import time
import json
import threading
import logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory store fallback for v0 usage metering.
# Structure: { "metering:{agent_id}": {"total_calls": int, "total_payment_amount": float, "last_used": float} }
_usage_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

_redis_client = None
if settings.REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Usage Metering initialized with Redis backend.")
    except ImportError:
        logger.warning("REDIS_URL is set but redis-py is not installed. Falling back to in-memory metering.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}. Falling back to in-memory metering.")

def record_usage(agent_id: str, payment_amount: float = 0.0) -> None:
    """
    Records a usage event for the given agent.
    Thread-safe for FastAPI concurrency.
    """
    now = time.time()
    key = f"metering:{agent_id}"
    
    if _redis_client:
        try:
            pipeline = _redis_client.pipeline()
            pipeline.hincrby(key, "total_calls", 1)
            if payment_amount > 0:
                pipeline.hincrbyfloat(key, "total_payment_amount", payment_amount)
            pipeline.hset(key, "last_used", now)
            pipeline.execute()
            logger.debug(f"Recorded usage for {agent_id} (Redis): +1 call, +{payment_amount} payment")
        except Exception as e:
            logger.error(f"Redis metering error: {e}. Falling back to in-memory for this request.")
            _record_usage_in_memory(key, agent_id, payment_amount, now)
    else:
        _record_usage_in_memory(key, agent_id, payment_amount, now)
    
    # Also track in the new analytics module (Day 32)
    from app.analytics import track_analytics_event
    track_analytics_event(agent_id, "proxy_execute", payment_amount)

def _record_usage_in_memory(key: str, agent_id: str, payment_amount: float, now: float) -> None:
    with _lock:
        if key not in _usage_store:
            _usage_store[key] = {
                "total_calls": 0,
                "total_payment_amount": 0.0,
                "last_used": 0.0
            }
        
        _usage_store[key]["total_calls"] += 1
        if payment_amount and payment_amount > 0:
            _usage_store[key]["total_payment_amount"] += payment_amount
        _usage_store[key]["last_used"] = now
        
    logger.debug(f"Recorded usage for {agent_id} (in-memory): +1 call, +{payment_amount} payment")

def get_usage_stats(agent_id: str) -> Dict[str, Any]:
    """
    Retrieves the current usage statistics for the given agent.
    """
    key = f"metering:{agent_id}"
    
    if _redis_client:
        try:
            data = _redis_client.hgetall(key)
            if data:
                return {
                    "total_calls": int(data.get("total_calls", 0)),
                    "total_payment_amount": float(data.get("total_payment_amount", 0.0)),
                    "last_used": float(data.get("last_used", 0.0))
                }
        except Exception as e:
            logger.error(f"Redis metering fetch error: {e}. Falling back to in-memory.")

    with _lock:
        # Return a copy to prevent accidental mutation by the caller
        stats = _usage_store.get(key, {
            "total_calls": 0,
            "total_payment_amount": 0.0,
            "last_used": 0.0
        })
        return dict(stats)

def get_total_agents_metered() -> int:
    """
    Returns the total number of unique agents that have been metered.
    """
    if _redis_client:
        try:
            # Scan for keys matching metering:*
            cursor = '0'
            count = 0
            while cursor != 0:
                cursor, keys = _redis_client.scan(cursor=cursor, match="metering:*", count=100)
                count += len(keys)
            return count
        except Exception as e:
            logger.error(f"Redis metering count error: {e}. Falling back to in-memory.")

    with _lock:
        return len(_usage_store)

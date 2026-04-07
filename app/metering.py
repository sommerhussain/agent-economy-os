"""
Universal Agent Economy OS - Usage Metering

This module provides a thread-safe, in-memory usage metering store for v0.
It tracks total calls and total payment amounts per agent_id to lay the
groundwork for future billing and analytics. It will be swapped out for
Redis or a persistent database in the future.
"""
import time
import threading
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# In-memory store for v0 usage metering.
# Structure: { "agent_id": {"total_calls": int, "total_payment_amount": float, "last_used": float} }
# In the future, this will be replaced by a persistent database or Redis.
_usage_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def record_usage(agent_id: str, payment_amount: float = 0.0) -> None:
    """
    Records a usage event for the given agent.
    Thread-safe for FastAPI concurrency.
    """
    with _lock:
        if agent_id not in _usage_store:
            _usage_store[agent_id] = {
                "total_calls": 0,
                "total_payment_amount": 0.0,
                "last_used": 0.0
            }
        
        _usage_store[agent_id]["total_calls"] += 1
        if payment_amount and payment_amount > 0:
            _usage_store[agent_id]["total_payment_amount"] += payment_amount
        _usage_store[agent_id]["last_used"] = time.time()
        
    logger.debug(f"Recorded usage for {agent_id}: +1 call, +{payment_amount} payment")
    
    # Also track in the new analytics module (Day 32)
    from app.analytics import track_analytics_event
    track_analytics_event(agent_id, "proxy_execute", payment_amount)

def get_usage_stats(agent_id: str) -> Dict[str, Any]:
    """
    Retrieves the current usage statistics for the given agent.
    """
    with _lock:
        # Return a copy to prevent accidental mutation by the caller
        stats = _usage_store.get(agent_id, {
            "total_calls": 0,
            "total_payment_amount": 0.0,
            "last_used": 0.0
        })
        return dict(stats)

def get_total_agents_metered() -> int:
    """
    Returns the total number of unique agents that have been metered.
    """
    with _lock:
        return len(_usage_store)


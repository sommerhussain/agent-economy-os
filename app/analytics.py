"""
Universal Agent Economy OS - Usage Analytics

This module provides a thread-safe, in-memory analytics tracker for v0.
It tracks recent activity and aggregates global usage statistics.
It is structured to be easily swapped out for Redis (e.g., using lists for recent activity
and sorted sets for time-series data).
"""
import time
import logging
import threading
from typing import Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AnalyticsEvent(BaseModel):
    """
    Represents a single analytics event (e.g., proxy execution, payment).
    """
    event_id: str
    agent_id: str
    event_type: str
    amount: float = 0.0
    timestamp: float

class AnalyticsTracker:
    """
    A Redis-ready analytics tracker.
    Currently uses in-memory lists and dicts, but keys and logic are structured
    like a future Redis implementation (e.g., LPUSH, LTRIM, HINCRBY).
    """
    def __init__(self):
        # Redis-like keys:
        # "analytics:recent_activity" -> List[Dict]
        # "analytics:global:total_calls" -> int
        # "analytics:global:total_revenue" -> float
        # "analytics:active_agents" -> Dict[str, float] (agent_id -> last_active_timestamp)
        self._store: Dict[str, Any] = {
            "analytics:recent_activity": [],
            "analytics:global:total_calls": 0,
            "analytics:global:total_revenue": 0.0,
            "analytics:active_agents": {}
        }
        self._lock = threading.Lock()

    def track_event(self, event: AnalyticsEvent) -> None:
        """
        Tracks a new analytics event.
        Updates global counters and recent activity list.
        """
        from app.config import settings
        max_recent = settings.ANALYTICS_MAX_RECENT_EVENTS
        
        with self._lock:
            # Update global counters (like Redis INCRBY/INCRBYFLOAT)
            if event.event_type == "proxy_execute":
                self._store["analytics:global:total_calls"] += 1
            if event.amount > 0:
                self._store["analytics:global:total_revenue"] += event.amount
            
            # Update active agents (like Redis ZADD)
            self._store["analytics:active_agents"][event.agent_id] = event.timestamp
            
            # Add to recent activity (like Redis LPUSH)
            self._store["analytics:recent_activity"].insert(0, event.model_dump())
            
            # Trim recent activity (like Redis LTRIM)
            if len(self._store["analytics:recent_activity"]) > max_recent:
                self._store["analytics:recent_activity"] = self._store["analytics:recent_activity"][:max_recent]

    def get_global_stats(self) -> Dict[str, Any]:
        """
        Retrieves aggregated global statistics.
        """
        from app.config import settings
        active_window_seconds = settings.ANALYTICS_ACTIVE_WINDOW_SECONDS
        
        now = time.time()
        with self._lock:
            total_calls = self._store["analytics:global:total_calls"]
            total_revenue = self._store["analytics:global:total_revenue"]
            
            # Count active agents within the window (like Redis ZCOUNT)
            active_agents = sum(
                1 for ts in self._store["analytics:active_agents"].values()
                if now - ts <= active_window_seconds
            )
            total_agents = len(self._store["analytics:active_agents"])
            
            recent_activity = list(self._store["analytics:recent_activity"][:10])
            
            return {
                "total_agents_registered": total_agents,
                "total_calls": total_calls,
                "total_revenue": total_revenue,
                "active_agents": active_agents,
                "recent_activity": recent_activity
            }

# Global singleton instance
_tracker = AnalyticsTracker()

def track_analytics_event(agent_id: str, event_type: str, amount: float = 0.0) -> None:
    """
    Helper to track an analytics event.
    """
    import uuid
    event = AnalyticsEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        agent_id=agent_id,
        event_type=event_type,
        amount=amount,
        timestamp=time.time()
    )
    _tracker.track_event(event)

def get_analytics_stats() -> Dict[str, Any]:
    """
    Helper to retrieve aggregated analytics stats.
    """
    return _tracker.get_global_stats()

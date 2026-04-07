"""
Universal Agent Economy OS - Rate Limiting

This module provides a thread-safe, in-memory rate limiter for v0.
It tracks request timestamps per agent_id and enforces a maximum number of
requests per window (e.g., 10 req/min). It is structured to be easily
swapped out for Redis (Day 26).
"""
import time
import logging
import threading
from typing import Tuple, Dict, List
from app.config import settings

logger = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Exception raised when an agent exceeds their rate limit."""
    def __init__(self, retry_after: int, detail: str):
        self.retry_after = retry_after
        self.detail = detail
        super().__init__(self.detail)

class RateLimiter:
    """
    A Redis-ready rate limiter structure.
    Currently uses an in-memory dictionary, but keys and logic are structured
    exactly like a future Redis ZSET implementation.
    """
    def __init__(self):
        self._store: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, agent_id: str) -> Tuple[bool, int]:
        """
        Checks if the given agent_id has exceeded the rate limit.
        Returns a tuple of (allowed: bool, retry_after_seconds: int).
        """
        now = time.time()
        key = f"rate_limit:{agent_id}"
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS

        with self._lock:
            if key not in self._store:
                self._store[key] = []
            
            # Clean up old timestamps outside the window (like ZREMRANGEBYSCORE in Redis)
            self._store[key] = [ts for ts in self._store[key] if now - ts < window]
            
            if len(self._store[key]) >= max_requests:
                # Calculate how long until the oldest request in the window expires
                oldest_request = self._store[key][0]
                retry_after = int(window - (now - oldest_request))
                retry_after = max(1, retry_after)
                logger.warning(f"Rate limit hit for {agent_id}. Retry after {retry_after}s.")
                return False, retry_after
                
            # Record the new request (like ZADD in Redis)
            self._store[key].append(now)
            return True, 0

# Global singleton instance
_limiter = RateLimiter()

def check_rate_limit(agent_id: str) -> Tuple[bool, int]:
    """
    Checks if the given agent_id has exceeded the rate limit.
    Returns a tuple of (allowed: bool, retry_after_seconds: int).
    """
    return _limiter.is_allowed(agent_id)

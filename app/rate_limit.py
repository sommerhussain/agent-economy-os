"""
Universal Agent Economy OS - Rate Limiting

This module provides a Redis-ready rate limiter for v0.
It tracks request timestamps per agent_id and enforces a maximum number of
requests per window (e.g., 10 req/min). It uses Redis if REDIS_URL is configured,
otherwise it falls back to a thread-safe in-memory dictionary structured exactly
like a Redis ZSET implementation.
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
    Uses Redis if REDIS_URL is set, otherwise falls back to an in-memory dictionary.
    Keys and logic are structured exactly like a Redis ZSET implementation.
    """
    def __init__(self):
        self._store: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._redis_client = None
        
        if settings.REDIS_URL: # pragma: no cover
            try:
                import redis
                self._redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("RateLimiter initialized with Redis backend.")
            except ImportError:
                logger.warning("REDIS_URL is set but redis-py is not installed. Falling back to in-memory rate limiting.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}. Falling back to in-memory rate limiting.")

    def is_allowed(self, agent_id: str) -> Tuple[bool, int]:
        """
        Checks if the given agent_id has exceeded the rate limit.
        Returns a tuple of (allowed: bool, retry_after_seconds: int).
        """
        now = time.time()
        key = f"rate_limit:{agent_id}"
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS

        if self._redis_client:
            try:
                pipeline = self._redis_client.pipeline()
                # Remove timestamps older than the window
                pipeline.zremrangebyscore(key, "-inf", now - window)
                # Add the current timestamp
                pipeline.zadd(key, {str(now): now})
                # Count the number of requests in the window
                pipeline.zcard(key)
                # Set an expiry on the key to clean it up automatically
                pipeline.expire(key, window)
                
                results = pipeline.execute()
                request_count = results[2]
                
                if request_count > max_requests:
                    # Get the oldest timestamp in the window to calculate retry_after
                    oldest_records = self._redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest_records:
                        oldest_ts = oldest_records[0][1]
                        retry_after = int(window - (now - oldest_ts))
                        retry_after = max(1, retry_after)
                    else:
                        retry_after = window
                    logger.warning(f"Rate limit hit for {agent_id} (Redis). Retry after {retry_after}s.")
                    return False, retry_after
                
                return True, 0
            except Exception as e:
                logger.error(f"Redis rate limiting error: {e}. Falling back to in-memory for this request.")
                # Fall through to in-memory logic if Redis fails

        # In-memory fallback logic
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

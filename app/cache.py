"""
Universal Agent Economy OS - Identity Caching Layer

This module provides a Redis-ready caching layer for identity data
(credentials and scopes). It uses Redis if REDIS_URL is configured,
otherwise it falls back to a thread-safe in-memory dictionary with TTL.
"""
import time
import json
import threading
import logging
from typing import Optional, Dict, Any, Tuple, List
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory stores fallback
# _cred_cache: {"cred:{agent_id}:{credential_type}": {"secret_data": dict, "scopes": list, "expires_at": float}}
_cred_cache: Dict[str, Dict[str, Any]] = {}
# _scopes_cache: {"scopes:{agent_id}": {"scopes_dict": dict, "expires_at": float}}
_scopes_cache: Dict[str, Dict[str, Any]] = {}

_lock = threading.Lock()
DEFAULT_TTL_SECONDS = 300  # 5 minutes

_redis_client = None
if settings.REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Identity Cache initialized with Redis backend.")
    except ImportError:
        logger.warning("REDIS_URL is set but redis-py is not installed. Falling back to in-memory cache.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}. Falling back to in-memory cache.")

def get_cached_credential(agent_id: str, credential_type: str) -> Optional[Tuple[Dict[str, Any], List[str]]]:
    """
    Retrieves a cached credential and its scopes if it exists and has not expired.
    """
    key = f"cred:{agent_id}:{credential_type}"
    
    if _redis_client:
        try:
            data = _redis_client.get(key)
            if data:
                logger.debug(f"Cache hit for credential (Redis): {agent_id} / {credential_type}")
                parsed = json.loads(data)
                return parsed["secret_data"], parsed["scopes"]
            return None
        except Exception as e:
            logger.error(f"Redis cache error: {e}. Falling back to in-memory.")

    with _lock:
        entry = _cred_cache.get(key)
        if entry:
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache hit for credential: {agent_id} / {credential_type}")
                return entry["secret_data"], entry["scopes"]
            else:
                logger.debug(f"Cache expired for credential: {agent_id} / {credential_type}")
                del _cred_cache[key]
        return None

def set_cached_credential(agent_id: str, credential_type: str, secret_data: Dict[str, Any], scopes: List[str], ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """
    Caches a credential and its scopes with a TTL.
    """
    key = f"cred:{agent_id}:{credential_type}"
    
    if _redis_client:
        try:
            payload = json.dumps({"secret_data": secret_data, "scopes": scopes})
            _redis_client.setex(key, ttl, payload)
            return
        except Exception as e:
            logger.error(f"Redis cache set error: {e}. Falling back to in-memory.")

    with _lock:
        _cred_cache[key] = {
            "secret_data": secret_data,
            "scopes": scopes,
            "expires_at": time.time() + ttl
        }

def get_cached_agent_scopes(agent_id: str) -> Optional[Dict[str, List[str]]]:
    """
    Retrieves cached agent scopes if they exist and have not expired.
    """
    key = f"scopes:{agent_id}"
    
    if _redis_client:
        try:
            data = _redis_client.get(key)
            if data:
                logger.debug(f"Cache hit for scopes (Redis): {agent_id}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis cache error: {e}. Falling back to in-memory.")

    with _lock:
        entry = _scopes_cache.get(key)
        if entry:
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache hit for scopes: {agent_id}")
                return entry["scopes_dict"]
            else:
                logger.debug(f"Cache expired for scopes: {agent_id}")
                del _scopes_cache[key]
        return None

def set_cached_agent_scopes(agent_id: str, scopes_dict: Dict[str, List[str]], ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """
    Caches agent scopes with a TTL.
    """
    key = f"scopes:{agent_id}"
    
    if _redis_client:
        try:
            _redis_client.setex(key, ttl, json.dumps(scopes_dict))
            return
        except Exception as e:
            logger.error(f"Redis cache set error: {e}. Falling back to in-memory.")

    with _lock:
        _scopes_cache[key] = {
            "scopes_dict": scopes_dict,
            "expires_at": time.time() + ttl
        }

def invalidate_agent_cache(agent_id: str) -> None:
    """
    Invalidates all cached credentials and scopes for a given agent.
    Called during credential rotation or agent updates.
    """
    if _redis_client:
        try:
            # Delete scopes
            _redis_client.delete(f"scopes:{agent_id}")
            # Delete credentials (scan for keys matching cred:{agent_id}:*)
            cursor = '0'
            while cursor != 0:
                cursor, keys = _redis_client.scan(cursor=cursor, match=f"cred:{agent_id}:*", count=100)
                if keys:
                    _redis_client.delete(*keys)
            logger.info(f"Invalidated identity cache for agent (Redis): {agent_id}")
            return
        except Exception as e:
            logger.error(f"Redis cache invalidation error: {e}. Falling back to in-memory.")

    with _lock:
        # Remove scopes
        scopes_key = f"scopes:{agent_id}"
        if scopes_key in _scopes_cache:
            del _scopes_cache[scopes_key]
        
        # Remove credentials
        prefix = f"cred:{agent_id}:"
        keys_to_delete = [k for k in _cred_cache.keys() if k.startswith(prefix)]
        for k in keys_to_delete:
            del _cred_cache[k]
    logger.info(f"Invalidated identity cache for agent: {agent_id}")

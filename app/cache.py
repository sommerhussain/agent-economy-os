"""
Universal Agent Economy OS - Identity Caching Layer

This module provides a thread-safe, in-memory caching layer for identity data
(credentials and scopes). It uses a simple dictionary with TTL (time-to-live)
to reduce database load. Future-proofed for an easy swap to Redis (Day 26).
"""
import time
import threading
import logging
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

# In-memory stores
# _cred_cache: {(agent_id, credential_type): {"secret_data": dict, "scopes": list, "expires_at": float}}
_cred_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
# _scopes_cache: {agent_id: {"scopes_dict": dict, "expires_at": float}}
_scopes_cache: Dict[str, Dict[str, Any]] = {}

_lock = threading.Lock()
DEFAULT_TTL_SECONDS = 300  # 5 minutes

def get_cached_credential(agent_id: str, credential_type: str) -> Optional[Tuple[Dict[str, Any], List[str]]]:
    """
    Retrieves a cached credential and its scopes if it exists and has not expired.
    """
    with _lock:
        key = (agent_id, credential_type)
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
    with _lock:
        _cred_cache[(agent_id, credential_type)] = {
            "secret_data": secret_data,
            "scopes": scopes,
            "expires_at": time.time() + ttl
        }

def get_cached_agent_scopes(agent_id: str) -> Optional[Dict[str, List[str]]]:
    """
    Retrieves cached agent scopes if they exist and have not expired.
    """
    with _lock:
        entry = _scopes_cache.get(agent_id)
        if entry:
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache hit for scopes: {agent_id}")
                return entry["scopes_dict"]
            else:
                logger.debug(f"Cache expired for scopes: {agent_id}")
                del _scopes_cache[agent_id]
        return None

def set_cached_agent_scopes(agent_id: str, scopes_dict: Dict[str, List[str]], ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """
    Caches agent scopes with a TTL.
    """
    with _lock:
        _scopes_cache[agent_id] = {
            "scopes_dict": scopes_dict,
            "expires_at": time.time() + ttl
        }

def invalidate_agent_cache(agent_id: str) -> None:
    """
    Invalidates all cached credentials and scopes for a given agent.
    Called during credential rotation or agent updates.
    """
    with _lock:
        # Remove scopes
        if agent_id in _scopes_cache:
            del _scopes_cache[agent_id]
        
        # Remove credentials
        keys_to_delete = [k for k in _cred_cache.keys() if k[0] == agent_id]
        for k in keys_to_delete:
            del _cred_cache[k]
    logger.info(f"Invalidated identity cache for agent: {agent_id}")

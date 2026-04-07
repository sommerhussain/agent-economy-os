"""
Universal Agent Economy OS - A2A Routing Engine

This module provides the basic A2A (Agent-to-Agent) routing stub. It determines
whether a tool call should be routed to another agent within the ecosystem or
executed as a standard downstream HTTP request. Future-proofed for full A2A
routing and integration tests (Day 21).
"""
import logging
import httpx
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.cache import get_cached_agent_scopes

logger = logging.getLogger(__name__)

class A2ARouteRequest(BaseModel):
    """
    Payload for a direct Agent-to-Agent routing request.
    """
    source_agent_id: str = Field(..., description="Agent initiating the call", examples=["agent_alpha"])
    target_agent_id: str = Field(..., description="Agent receiving the call", examples=["agent_beta"])
    tool_call: Dict[str, Any] = Field(..., description="The tool execution payload", examples=[{"action": "transfer_funds"}])

class A2ARouteResponse(BaseModel):
    """
    Response payload for a direct A2A routing request.
    """
    success: bool = Field(..., description="Whether the A2A route was successful", examples=[True])
    message: str = Field(..., description="Routing status message", examples=["A2A routing stub executed successfully."])

async def execute_downstream_tool(tool_call: Dict[str, Any]) -> bool:
    """
    Executes the downstream A2A tool call.
    Expects 'url' and 'method' in the tool_call payload.
    In the future, this will include retry logic, circuit breakers, and real authentication.
    """
    url = tool_call.get("url")
    method = tool_call.get("method", "POST")

    if not url:
        logger.error("Downstream execution failed: 'url' missing from tool_call payload.")
        return False

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Routing tool call to downstream: {method} {url}")
            response = await client.request(method=method, url=url, json=tool_call)
            
            if response.is_success:
                logger.info(f"Downstream call successful: {response.status_code}")
                return True
            else:
                logger.error(f"Downstream call failed with status {response.status_code}: {response.text}")
                return False
    except httpx.RequestError as e:
        logger.error(f"Downstream connection error: {str(e)}")
        return False

async def route_tool_call(source_agent_id: str, tool_call: Dict[str, Any]) -> bool:
    """
    Routes the tool call either to another agent (A2A) or to a downstream HTTP URL.
    Checks cache for agent scopes and validates target.
    """
    target_agent_id = tool_call.get("target_agent_id")
    
    if target_agent_id:
        # A2A Routing Stub
        logger.info(f"A2A Routing Event: {source_agent_id} -> {target_agent_id}")
        
        # Check cache for target agent scopes as a future-proof stub
        scopes = get_cached_agent_scopes(target_agent_id)
        if scopes is not None:
            logger.debug(f"Target agent {target_agent_id} found in cache with scopes: {scopes}")
        else:
            logger.debug(f"Target agent {target_agent_id} not in cache, proceeding with stub.")
            
        return True
        
    # Fallback to standard downstream HTTP execution
    return await execute_downstream_tool(tool_call)

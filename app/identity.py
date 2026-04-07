"""
Universal Agent Economy OS - Identity Engine

This module provides the core identity management for autonomous agents.
It handles agent registration, establishing the foundational record required
for future MCP/A2A operations, credential issuance, and usage metering.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.supabase import create_tables, insert_agent, rotate_credential_db
from app.cache import invalidate_agent_cache

logger = logging.getLogger(__name__)

def check_scopes(requested_scopes: List[str], granted_scopes: List[str]) -> bool:
    """
    Validates that all requested scopes are present in the granted scopes.
    Future-proofed for full permission engine (Day 19 caching, Day 20 routing).
    """
    if not requested_scopes:
        return True
    if not granted_scopes:
        return False
    return all(scope in granted_scopes for scope in requested_scopes)

class AgentRegisterRequest(BaseModel):
    """
    Payload for registering a new autonomous agent.
    """
    agent_id: str = Field(
        ..., 
        description="Unique identifier for the new agent", 
        examples=["agent_456"]
    )
    name: str = Field(
        ..., 
        description="Human-readable name for the agent", 
        examples=["Trading Bot Alpha"]
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Optional JSON metadata for the agent", 
        examples=[{"version": "1.0", "region": "us-east"}]
    )

class AgentResponse(BaseModel):
    """
    Response payload returning the result of the agent registration.
    """
    success: bool = Field(
        ..., 
        description="Whether the registration was successful",
        examples=[True]
    )
    agent_id: str = Field(
        ..., 
        description="Unique identifier for the registered agent",
        examples=["agent_456"]
    )
    name: str = Field(
        ..., 
        description="Name of the registered agent",
        examples=["Trading Bot Alpha"]
    )
    created_at: str = Field(
        ..., 
        description="ISO timestamp of registration",
        examples=["2026-04-05T12:00:00Z"]
    )

async def register_agent(request: AgentRegisterRequest) -> AgentResponse:
    """
    Registers a new agent in the Identity Engine.
    Ensures the schema is bootstrapped, then inserts the agent record.
    Future-proofed for credential rotation (Day 17) and permission checking (Day 18).
    """
    logger.info(f"Registering new agent: {request.agent_id}")
    
    # Ensure tables exist (idempotent)
    create_tables()
    
    # Insert the agent into the database (or simulate)
    success = insert_agent(
        agent_id=request.agent_id,
        name=request.name,
        metadata=request.metadata
    )
    
    # In the future (Day 17), we might automatically generate and return a default credential stub here.
    
    return AgentResponse(
        success=success,
        agent_id=request.agent_id,
        name=request.name,
        created_at=datetime.now(timezone.utc).isoformat()
    )

class CredentialRotateRequest(BaseModel):
    """
    Payload for rotating or issuing a new credential for an agent.
    """
    agent_id: str = Field(
        ..., 
        description="Unique identifier for the agent", 
        examples=["agent_456"]
    )
    credential_type: str = Field(
        ..., 
        description="Type of credential to rotate (e.g., 'stripe_live', 'aws_s3')", 
        examples=["stripe_live"]
    )
    new_secret_data: Dict[str, Any] = Field(
        ..., 
        description="New secret data JSON to securely store", 
        examples=[{"api_key": "sk_live_new123456"}]
    )
    expires_in_days: Optional[float] = Field(
        None, 
        description="Optional number of days until the new credential expires", 
        examples=[30.0]
    )

class CredentialRotateResponse(BaseModel):
    """
    Response payload returning the result of the credential rotation.
    """
    success: bool = Field(
        ..., 
        description="Whether the rotation was successful",
        examples=[True]
    )
    agent_id: str = Field(
        ..., 
        description="Unique identifier for the agent",
        examples=["agent_456"]
    )
    credential_type: str = Field(
        ..., 
        description="Type of credential rotated",
        examples=["stripe_live"]
    )
    expires_at: Optional[str] = Field(
        None, 
        description="ISO timestamp of when the new credential expires (if applicable)",
        examples=["2026-05-05T12:00:00Z"]
    )

async def rotate_credential(request: CredentialRotateRequest) -> CredentialRotateResponse:
    """
    Rotates or issues a new credential for an autonomous agent.
    Calculates the time-based expiry and delegates the upsert to Supabase.
    Future-proofed for permission checking (Day 18).
    """
    logger.info(f"Rotating {request.credential_type} credential for agent: {request.agent_id}")
    
    # Calculate expiry if provided
    expires_at_iso = None
    if request.expires_in_days is not None and request.expires_in_days > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)
        expires_at_iso = expires_at.isoformat()
        
    # Upsert the credential into the database (or simulate)
    success = rotate_credential_db(
        agent_id=request.agent_id,
        credential_type=request.credential_type,
        new_secret_data=request.new_secret_data,
        expires_at=expires_at_iso
    )
    
    # Invalidate the cache for this agent so the new credential takes effect immediately
    if success:
        invalidate_agent_cache(request.agent_id)
    
    return CredentialRotateResponse(
        success=success,
        agent_id=request.agent_id,
        credential_type=request.credential_type,
        expires_at=expires_at_iso
    )

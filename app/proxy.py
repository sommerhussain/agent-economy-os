"""
Universal Agent Economy OS - Proxy Execution Engine

This module handles the core business logic of the proxy. It orchestrates rate limiting,
credential injection (via Identity Engine), settlement (via x402 micropayments),
downstream A2A tool execution, audit logging, and usage metering.
"""
import uuid
import logging
from app.routing import route_tool_call
from app.payments import handle_payment
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.errors import InsufficientScopesError
from app.supabase import fetch_credential
from app.audit import generate_audit_id, log_request
from app.rate_limit import check_rate_limit, RateLimitExceeded
from app.metering import record_usage

logger = logging.getLogger(__name__)

class ProxyRequest(BaseModel):
    """
    Core payload for agent-to-agent or agent-to-tool proxy execution.
    """
    agent_id: str = Field(
        ..., 
        description="Unique identifier for the calling agent",
        examples=["agent_123"]
    )
    tool_call: Dict[str, Any] = Field(
        ..., 
        description="The tool execution payload or parameters",
        examples=[{
            "url": "https://api.example.com/data",
            "method": "POST",
            "payload": {"query": "test"}
        }]
    )
    credential_type: str = Field(
        ..., 
        description="Type of credential to inject (e.g., 'stripe', 'aws', 'custom_oauth')",
        examples=["stripe_live"]
    )
    payment_amount: Optional[float] = Field(
        None, 
        description="Optional x402 payment amount for the transaction",
        examples=[0.05]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "agent_id": "agent_123",
                "tool_call": {
                    "url": "https://api.example.com/data",
                    "method": "POST",
                    "payload": {"query": "test"}
                },
                "credential_type": "stripe_live",
                "payment_amount": 0.05
            }
        }
    }

class ProxyResponse(BaseModel):
    """
    Response payload returning the result of the proxy execution and settlement.
    """
    success: bool = Field(
        ..., 
        description="Whether the proxy execution was successful",
        examples=[True]
    )
    injected_credential: bool = Field(
        ..., 
        description="Whether credentials were successfully injected",
        examples=[True]
    )
    x402_settled: bool = Field(
        ..., 
        description="Whether the x402 micropayment was settled",
        examples=[True]
    )
    transaction_id: Optional[str] = Field(
        None, 
        description="Unique transaction ID if a payment was settled",
        examples=["tx_a1b2c3d4e5f6"]
    )
    audit_id: str = Field(
        ..., 
        description="Unique audit trail ID for the transaction",
        examples=["adt_9876543210abcdef"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "injected_credential": True,
                "x402_settled": True,
                "transaction_id": "tx_a1b2c3d4e5f6",
                "audit_id": "adt_9876543210abcdef"
            }
        }
    }

async def execute_proxy_request(request: ProxyRequest) -> ProxyResponse:
    """
    Core proxy execution logic.
    Currently stubbed for v0. Future modules (Identity, Settlement, Compliance)
    will hook into this pipeline without breaking the core signature.
    """
    logger.info(f"Executing proxy request for agent: {request.agent_id}")
    
    # 0. Rate Limiting
    allowed, retry_after = check_rate_limit(request.agent_id)
    if not allowed:
        raise RateLimitExceeded(
            retry_after=retry_after,
            detail=f"Rate limit exceeded for agent '{request.agent_id}'. Please try again in {retry_after} seconds."
        )
        
    # 1. Identity Engine / Credential Injection via Supabase
    required_scopes = request.tool_call.get("required_scopes")
    credentials = fetch_credential(request.agent_id, request.credential_type, required_scopes)
    injected = False
    
    if required_scopes and not credentials:
        logger.warning(f"Failing fast: Insufficient scopes or missing credential for {request.agent_id}")
        raise InsufficientScopesError(required_scopes=required_scopes)
        
    if credentials:
        # Inject credentials into the tool call payload securely
        request.tool_call["_injected_credentials"] = credentials
        injected = True
        logger.info(f"Successfully injected {request.credential_type} credentials into tool_call payload.")
    else:
        logger.warning(f"Failed to find credentials for {request.agent_id} ({request.credential_type}).")

    # 2. Settlement Engine (x402 micropayment proxy)
    settled = False
    transaction_id = None
    if request.payment_amount is not None:
        settled, transaction_id, _ = handle_payment(request.payment_amount, request.agent_id)

    # 3. Tool Execution Engine
    # Route the injected tool_call to the target A2A endpoint
    if not injected:
        logger.warning("Tool execution proceeding without injected credentials. This may fail downstream.")
        
    success = await route_tool_call(request.agent_id, request.tool_call)

    # 4. Compliance & Audit Logging
    audit_id = generate_audit_id()
    log_request(
        audit_id=audit_id,
        agent_id=request.agent_id,
        credential_type=request.credential_type,
        payment_amount=request.payment_amount,
        success=success
    )

    # 5. Usage Metering
    # Record the usage for future billing and analytics (Day 23)
    record_usage(agent_id=request.agent_id, payment_amount=request.payment_amount or 0.0)

    return ProxyResponse(
        success=success,
        injected_credential=injected,
        x402_settled=settled,
        transaction_id=transaction_id,
        audit_id=audit_id
    )

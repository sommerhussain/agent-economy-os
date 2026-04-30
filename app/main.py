"""
Universal Agent Economy OS - Main Application Gateway

This module serves as the primary entry point for the UAE OS proxy. It configures
FastAPI, wires up all middleware (CORS, Security, Auth), and exposes the core
endpoints (/proxy/execute, /health, /metrics).
"""
import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware
from app.proxy import ProxyRequest, ProxyResponse, execute_proxy_request
from app.identity import AgentRegisterRequest, AgentResponse, register_agent, CredentialRotateRequest, CredentialRotateResponse, rotate_credential
from app.routing import A2ARouteRequest, A2ARouteResponse, route_tool_call
from app.payments import PaymentWebhookPayload, process_payment_webhook, verify_webhook_signature, handle_stripe_webhook
from app.billing import Invoice, calculate_usage_invoice, get_recent_invoices
from app.rate_limit import RateLimitExceeded
from app.errors import UAEError
from app.config import settings
from app.auth import api_key_middleware
from app.metering import get_total_agents_metered
from app.analytics import get_analytics_stats, AnalyticsEvent
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field

# Configure basic logging for the proxy
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

VERSION = "0.1.10"
START_TIME = time.time()

app = FastAPI(
    title="Universal Agent Economy OS - Proxy API",
    description="v0 Proxy Skeleton for secure credential injection and x402 micropayments.",
    version=VERSION
)

from fastapi.staticfiles import StaticFiles

# Serve .well-known directory for MCP discovery
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="well-known")

# 1. CORS Middleware
# Uses the centralized config object for production readiness.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Observability & Request ID Middleware
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    """
    Generates a unique request_id for observability and logs the request.
    Future-proofed for OpenTelemetry tracing.
    """
    request_id = f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id
    
    logger.info(f"Incoming request {request.method} {request.url.path} [req_id: {request_id}]")
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(f"Unhandled error in request [req_id: {request_id}]: {str(e)}", exc_info=True)
        raise

# 3. Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Adds basic security headers to all responses.
    In the future, this can be expanded into a dedicated security module.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# 4. Authentication Middleware - ONLY protect non-public routes
@app.middleware("http")
async def conditional_auth_middleware(request: Request, call_next):
    """Skip authentication for public discovery and health check paths."""
    public_paths = [
        "/",
        "/health",
        "/metrics",
        "/verticals",
        "/stats",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    if (
        request.url.path in public_paths
        or request.url.path.startswith("/.well-known/")
        or request.url.path.startswith("/static/")
    ):
        return await call_next(request)

    # All other routes require authentication
    return await api_key_middleware(request, call_next)

@app.exception_handler(UAEError)
async def uae_error_handler(request: Request, exc: UAEError):
    """
    Global exception handler for all structured UAE errors.
    Returns a clean, consistent JSON response with error_code and request_id.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"UAEError: {exc.error_code} - {exc.message} [req_id: {request_id}]",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "request_id": request_id,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id
        }
    )

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": f"Universal Agent Economy OS Proxy v{VERSION} is running",
        "endpoints": ["/proxy/execute", "/health", "/metrics", "/stats", "/verticals"],
        "discovery": "Agent Card at /.well-known/agent-card.json, MCP Manifest at /.well-known/mcp.json",
        "note": "Revenue engine active - x402 + usage limits + paid discovery + daily/projected revenue tracking enabled. Use /verticals to explore available credential packs."
    }

@app.get("/.well-known/agent-card.json", include_in_schema=False)
async def get_agent_card():
    """
    Serves the agent discovery metadata for the Universal Agent Economy OS.
    """
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".well-known", "agent-card.json")
    if not os.path.exists(file_path): # pragma: no cover
        raise HTTPException(status_code=404, detail="Agent card not found")
    return FileResponse(file_path, media_type="application/json")

@app.get("/.well-known/mcp.json", include_in_schema=False)
async def get_mcp_manifest():
    """
    Serves the MCP server manifest for the Universal Agent Economy OS.
    """
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".well-known", "mcp.json")
    if not os.path.exists(file_path): # pragma: no cover
        raise HTTPException(status_code=404, detail="MCP manifest not found")
    return FileResponse(file_path, media_type="application/json")

@app.get("/health")
async def health_check():
    """
    Basic health check endpoint for load balancers and orchestrators.
    """
    from app.analytics import get_daily_revenue_summary
    return {
        "status": "healthy",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "revenue_ready": True,
        "revenue_note": "Revenue engine active with usage limits, paid discovery, and daily/projected revenue tracking",
        "daily_revenue_summary": get_daily_revenue_summary()
    }

@app.get("/metrics")
async def metrics():
    """
    Basic monitoring endpoint returning uptime and usage summary.
    Publicly accessible for easy monitoring.
    """
    uptime_seconds = time.time() - START_TIME
    return {
        "status": "active",
        "version": VERSION,
        "uptime_seconds": round(uptime_seconds, 2),
        "total_agents_metered": get_total_agents_metered()
    }

class AgentTierStatus(BaseModel):
    """
    Tier status and pricing projections for a specific agent.
    """
    tier: str = Field(..., description="Current pricing tier", examples=["free"])
    total_calls: int = Field(..., description="Total API calls made by the agent", examples=[45])
    limit: int = Field(..., description="API call limit for the current tier", examples=[100])
    remaining: int = Field(..., description="Remaining API calls before limit is reached", examples=[55])
    exceeded: bool = Field(..., description="Whether the agent has exceeded their limit", examples=[False])
    projected_cost: float = Field(..., description="Projected cost based on current usage and billing rate", examples=[0.45])
    tier_recommendation: str = Field(..., description="Recommended tier based on usage patterns", examples=["free"])

class DashboardStatsResponse(BaseModel):
    """
    Response payload for the basic usage stats dashboard.
    """
    total_agents_registered: int = Field(..., description="Total number of agents metered", examples=[42])
    total_calls: int = Field(..., description="Total API calls across all agents", examples=[15000])
    total_revenue: float = Field(..., description="Total settled payment volume across all agents", examples=[1250.50])
    daily_revenue_summary: Dict[str, float] = Field(..., description="Daily revenue summary and projections", examples=[{"daily_revenue": 150.25, "projected_7d_revenue": 1051.75, "projected_30d_revenue": 4507.50, "projected_annual_revenue": 54841.25}])
    active_agents: int = Field(..., description="Number of agents with recent activity (within 24h)", examples=[12])
    recent_activity: List[Dict[str, Any]] = Field(..., description="List of recent analytics events", examples=[[{"event_id": "evt_123", "agent_id": "agent_1", "event_type": "proxy_execute", "amount": 0.05, "timestamp": 1700000000.0}]])
    recent_invoices: List[Invoice] = Field(..., description="List of recently generated invoices")
    pricing_tiers: Dict[str, int] = Field(..., description="Current pricing tier limits", examples=[{"free": 100, "pro": 10000}])
    agent_tier_status: Optional[AgentTierStatus] = Field(None, description="Tier status for a specific agent if requested")

@app.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Usage Stats & Analytics Dashboard",
    response_description="Returns global usage statistics, recent activity events, and recent invoices.",
    responses={
        200: {
            "description": "Successful retrieval of global stats",
            "content": {
                "application/json": {
                    "example": {
                        "total_agents_registered": 150,
                        "total_calls": 45000,
                        "total_revenue": 3250.75,
                        "daily_revenue_summary": {
                            "daily_revenue": 150.25,
                            "projected_7d_revenue": 1051.75,
                            "projected_30d_revenue": 4507.50,
                            "projected_annual_revenue": 54841.25
                        },
                        "active_agents": 45,
                        "recent_activity": [
                            {
                                "event_id": "evt_123",
                                "agent_id": "agent_alpha",
                                "event_type": "proxy_execute",
                                "amount": 0.05,
                                "timestamp": 1700000000.0
                            }
                        ],
                        "recent_invoices": [],
                        "pricing_tiers": {
                            "free": 100,
                            "pro": 10000
                        },
                        "agent_tier_status": {
                            "tier": "free",
                            "total_calls": 45,
                            "limit": 100,
                            "remaining": 55,
                            "exceeded": False,
                            "projected_cost": 0.45,
                            "tier_recommendation": "free"
                        }
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def dashboard_stats(agent_id: Optional[str] = None):
    """
    Retrieves the global usage statistics and analytics dashboard.
    
    This endpoint aggregates data from the analytics tracker and billing engines,
    providing a real-time overview of the Universal Agent Economy OS health.
    It returns total agents, API calls, settlement revenue, daily revenue, recent activity, and pricing tiers.
    If an `agent_id` is provided, it also returns the tier status for that specific agent.
    """
    try:
        from app.limits import get_tier_status
        from app.analytics import get_daily_revenue_summary
        analytics_stats = get_analytics_stats()
        recent_invoices = get_recent_invoices()
        
        agent_status = None
        if agent_id:
            agent_status = get_tier_status(agent_id)
        
        return DashboardStatsResponse(
            total_agents_registered=analytics_stats["total_agents_registered"],
            total_calls=analytics_stats["total_calls"],
            total_revenue=analytics_stats["total_revenue"],
            daily_revenue_summary=get_daily_revenue_summary(),
            active_agents=analytics_stats["active_agents"],
            recent_activity=analytics_stats["recent_activity"],
            recent_invoices=recent_invoices,
            pricing_tiers={
                "free": settings.FREE_TIER_LIMIT,
                "pro": settings.PRO_TIER_LIMIT
            },
            agent_tier_status=agent_status
        )
    except Exception as e:
        logger.error(f"Failed to fetch dashboard stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching dashboard stats.")

@app.get(
    "/verticals",
    summary="List Vertical Credential Packs",
    response_description="Returns all registered vertical credential packs and their definitions.",
    responses={
        200: {
            "description": "Successful retrieval of vertical packs",
            "content": {
                "application/json": {
                    "example": {
                        "verticals": [
                            {
                                "pack_id": "finance",
                                "name": "Finance",
                                "description": "Core financial credentials for payments, banking, and ledger access.",
                                "credentials": {
                                    "stripe_live": {
                                        "name": "Stripe Live Key",
                                        "description": "Live Stripe API key for processing real payments.",
                                        "allowed_scopes": ["payment:read", "payment:write", "refund:write"]
                                    },
                                    "plaid_link": {
                                        "name": "Plaid Link Token",
                                        "description": "Plaid token for linking bank accounts.",
                                        "allowed_scopes": ["account:read", "transaction:read"]
                                    }
                                }
                            },
                            {
                                "pack_id": "data",
                                "name": "Data & Compute",
                                "description": "Core credentials for data access, AI compute, and cloud infrastructure.",
                                "credentials": {
                                    "openai_api": {
                                        "name": "OpenAI API Key",
                                        "description": "Access to OpenAI language models.",
                                        "allowed_scopes": ["model:read", "model:execute", "fine_tune:write"]
                                    }
                                }
                            },
                            {
                                "pack_id": "compute",
                                "name": "Compute & AI",
                                "description": "Core credentials for AI model inference and cloud compute resources.",
                                "credentials": {
                                    "aws_compute": {
                                        "name": "AWS Compute Access",
                                        "description": "AWS EC2 and Lambda compute access.",
                                        "allowed_scopes": ["ec2:manage", "lambda:invoke"]
                                    }
                                }
                            },
                            {
                                "pack_id": "onchain",
                                "name": "On-Chain Identity (ERC-8004)",
                                "description": "Core credentials for on-chain identity, wallets, and smart contract interactions.",
                                "credentials": {
                                    "erc8004_identity": {
                                        "name": "ERC-8004 Identity",
                                        "description": "On-chain identity profile and attestations.",
                                        "allowed_scopes": ["wallet:read", "nft:verify", "ens:resolve"]
                                    },
                                    "smart_contract_execution": {
                                        "name": "Smart Contract Execution",
                                        "description": "Credentials for executing state-changing transactions on smart contracts.",
                                        "allowed_scopes": ["contract:execute", "contract:deploy", "gas:sponsor"]
                                    }
                                }
                            },
                            {
                                "pack_id": "compliance",
                                "name": "Compliance & Governance",
                                "description": "Enterprise-grade credentials for audit logging, KYC, regulatory reporting, and smart contract audits.",
                                "credentials": {
                                    "audit_log_access": {
                                        "name": "Audit Log Access",
                                        "description": "Read-only access to immutable transaction and proxy execution audit logs.",
                                        "allowed_scopes": ["audit:read", "audit:export"]
                                    },
                                    "audit_report_generator": {
                                        "name": "Audit Report Generator",
                                        "description": "Capability to generate auditor-ready export reports of proxy execution logs.",
                                        "allowed_scopes": ["audit:export", "report:generate"]
                                    },
                                    "soc2_compliance_auditor": {
                                        "name": "SOC2 Compliance Auditor",
                                        "description": "Enterprise credentials for automated SOC2 compliance monitoring and evidence collection.",
                                        "allowed_scopes": ["audit:read", "compliance:verify", "evidence:collect"]
                                    }
                                }
                            },
                            {
                                "pack_id": "legal",
                                "name": "Legal & Compliance",
                                "description": "Enterprise-grade credentials for legal contracts, IP registries, court filings, and e-signatures.",
                                "credentials": {
                                    "legal_contract_access": {
                                        "name": "Legal Contract Access",
                                        "description": "Access to centralized legal contract repositories and lifecycle management systems.",
                                        "allowed_scopes": ["contract:read", "contract:write", "contract:draft"]
                                    }
                                }
                            },
                            {
                                "pack_id": "healthcare",
                                "name": "Healthcare & Life Sciences",
                                "description": "Enterprise-grade credentials for EHR systems, PHI access, and HIPAA-compliant data processing.",
                                "credentials": {
                                    "ehr_system_access": {
                                        "name": "EHR System API",
                                        "description": "Secure access to Electronic Health Record (EHR) systems (e.g., Epic, Cerner) via FHIR standards.",
                                        "allowed_scopes": ["ehr:read", "ehr:write", "patient:search"]
                                    },
                                    "phi_data_processor": {
                                        "name": "PHI Data Processor",
                                        "description": "Credentials for processing Protected Health Information (PHI) under strict least-privilege enforcement.",
                                        "allowed_scopes": ["phi:read", "phi:anonymize", "data:process"]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_vertical_packs():
    """
    Retrieves all registered vertical credential packs.
    
    Vertical packs define standardized credential types (e.g., Finance, Social)
    and their allowed scopes. The Identity Engine uses these packs to automatically
    validate requested scopes and inject default scopes during credential rotation.
    """
    from app.verticals import get_all_packs
    try:
        packs = get_all_packs()
        return {"verticals": [pack.model_dump() for pack in packs.values()]}
    except Exception as e:
        logger.error(f"Failed to fetch vertical packs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching vertical packs.")

@app.post(
    "/agents/register",
    response_model=AgentResponse,
    summary="Register a New Agent",
    response_description="The result of the agent registration.",
    responses={
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def agents_register(request: AgentRegisterRequest):
    """
    Registers a new autonomous agent in the Identity Engine.
    This establishes the core identity record required for future MCP/A2A operations,
    credential issuance, and usage metering.
    """
    try:
        logger.info(f"Received registration request for agent: {request.agent_id}")
        response = await register_agent(request)
        if not response.success:
            raise UAEError(error_code="REGISTRATION_FAILED", message="Failed to register agent in the database.", status_code=500)
        return response
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"Agent registration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred while processing the registration request."
        )

@app.post(
    "/credentials/rotate",
    response_model=CredentialRotateResponse,
    summary="Rotate Agent Credentials",
    response_description="The result of the credential rotation, including calculated expiry.",
    responses={
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def credentials_rotate(request: CredentialRotateRequest):
    """
    Rotates or issues a new credential for an autonomous agent.
    Supports optional time-based expiry for future permission checking (Day 18).
    Overwrites the old credential securely in the Identity Engine.
    """
    try:
        logger.info(f"Received credential rotation request for agent: {request.agent_id}")
        response = await rotate_credential(request)
        if not response.success:
            raise UAEError(error_code="ROTATION_FAILED", message="Failed to rotate credential in the database.", status_code=500)
        return response
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"Credential rotation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred while processing the credential rotation request."
        )

@app.get(
    "/agents/{agent_id}/scopes",
    summary="Get Agent Scopes",
    response_description="Returns the scopes granted to the agent per credential type.",
    responses={
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_agent_scopes_endpoint(agent_id: str):
    """
    Retrieves all granted scopes for an agent across all their credentials.
    Future-proofed for full permission engine caching (Day 19) and routing (Day 20).
    """
    from app.supabase import get_agent_scopes
    try:
        scopes = get_agent_scopes(agent_id)
        return {"agent_id": agent_id, "scopes": scopes}
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to fetch scopes for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while fetching agent scopes."
        )

@app.post(
    "/agents/{agent_id}/credentials/{credential_type}/self-heal",
    summary="Trigger Self-Healing Auto-Rotation",
    response_description="The result of the auto-rotation process.",
    responses={
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def trigger_self_healing(agent_id: str, credential_type: str):
    """
    Triggers the self-healing auto-credential rotation for a specific agent and credential type.
    
    This endpoint demonstrates the enterprise-grade zero-touch maintenance capability of the 
    Universal Agent Economy OS. It automatically generates a new secure secret, calculates the 
    appropriate expiry based on vertical-specific compliance rules, and seamlessly updates the 
    Identity Engine without manual intervention.
    """
    from app.identity import auto_rotate_agent_credentials
    try:
        logger.info(f"Received self-healing request for agent: {agent_id}, credential: {credential_type}")
        response = await auto_rotate_agent_credentials(agent_id, credential_type)
        if not response.get("success"):
            raise UAEError(error_code="SELF_HEAL_FAILED", message="Failed to apply self-healing rotation.", status_code=500)
        return response
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"Self-healing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred while processing the self-healing request."
        )

@app.post(
    "/a2a/route",
    response_model=A2ARouteResponse,
    summary="Direct A2A Routing Engine",
    response_description="Result of the direct A2A routing execution.",
    responses={
        200: {
            "description": "Successful A2A execution",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "A2A routing executed successfully."
                    }
                }
            }
        },
        400: {"description": "Bad Request - Invalid A2A routing target"},
        401: {"description": "Unauthorized - Missing or invalid API key"},
        500: {"description": "Internal Server Error"}
    }
)
async def a2a_route(request: A2ARouteRequest):
    """
    Direct endpoint for routing a tool call to another agent (Agent-to-Agent) using the Model Context Protocol (MCP).
    
    This endpoint acts as the core router for the MCP/A2A network. It validates
    source agent scopes, resolves the target agent, and securely forwards the payload.
    
    **Example Request:**
    ```json
    {
      "source_agent_id": "agent_alpha",
      "target_agent_id": "agent_beta",
      "tool_call": {
        "action": "transfer_funds",
        "amount": 100
      }
    }
    ```
    """
    try:
        logger.info(f"Received direct A2A route request: {request.source_agent_id} -> {request.target_agent_id}")
        # Inject target_agent_id into tool_call to trigger A2A path
        request.tool_call["target_agent_id"] = request.target_agent_id
        success = await route_tool_call(request.source_agent_id, request.tool_call)
        return A2ARouteResponse(
            success=success, 
            message="A2A routing stub executed successfully." if success else "A2A routing failed."
        )
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"A2A routing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during A2A routing.")

@app.get(
    "/billing/invoice/{agent_id}",
    response_model=Invoice,
    summary="Generate Agent Invoice",
    response_description="Generates a usage-based invoice for the specified agent.",
    responses={
        200: {
            "description": "Invoice generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "invoice_id": "inv_12345abcde",
                        "agent_id": "agent_alpha",
                        "total_calls": 150,
                        "total_payment_volume": 25.50,
                        "applied_rate": 0.01,
                        "amount_due": 1.50,
                        "status": "draft",
                        "generated_at": "2026-04-06T12:00:00Z"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Missing or invalid API key"},
        404: {"description": "Not Found - Agent not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_usage_invoice(agent_id: str):
    """
    Generates a usage-based billing invoice for a specific agent.
    
    It calculates the total API calls and applies the configured `BILLING_RATE_PER_CALL`.
    This endpoint is foundational for the future Stripe/PDF invoicing engine.
    """
    try:
        invoice = calculate_usage_invoice(agent_id)
        return invoice
    except UAEError as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to generate invoice for {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while generating the invoice.")

@app.post(
    "/webhooks/payment",
    summary="Payment Confirmation Webhook",
    response_description="Confirmation that the webhook was received.",
    responses={
        200: {
            "description": "Webhook received and verified successfully",
            "content": {
                "application/json": {
                    "example": {"status": "received"}
                }
            }
        },
        400: {"description": "Bad Request - Invalid HMAC signature"},
        402: {"description": "Payment Required - Payment failed to process"},
        500: {"description": "Internal Server Error"}
    }
)
async def payment_webhook(request: Request, payload: PaymentWebhookPayload):
    """
    Webhook handler for incoming payment confirmations (e.g., Stripe, Lightning).
    
    This endpoint is public but strictly protected by HMAC SHA256 signature verification
    using the `WEBHOOK_SECRET`. It updates the internal settlement engine upon
    successful payment confirmation.
    
    **Example Payload:**
    ```json
    {
      "transaction_id": "tx_stripe_12345",
      "status": "success",
      "amount": 10.50,
      "agent_id": "agent_alpha"
    }
    ```
    """
    try:
        # Extract the raw body for signature verification
        body = await request.body()
        
        # In a real Stripe integration, this would be 'Stripe-Signature'
        signature = request.headers.get("X-Webhook-Signature")
        
        if not verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature. Rejecting request.")
            raise UAEError(error_code="INVALID_SIGNATURE", message="Invalid webhook signature", status_code=400)
            
        success = await process_payment_webhook(payload)
        
        if not success:
            logger.warning(f"Webhook processed but payment was not successful: {payload.transaction_id}")
            
        return {"status": "received"}
    except UAEError as e:
        raise e
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to process payment webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the webhook.")

@app.post(
    "/webhooks/stripe",
    summary="Stripe Webhook Handler",
    response_description="Confirmation that the Stripe webhook was received.",
    responses={
        200: {"description": "Webhook received and verified successfully"},
        400: {"description": "Bad Request - Invalid signature or payload"},
        500: {"description": "Internal Server Error"}
    }
)
async def stripe_webhook(request: Request):
    """
    Webhook handler specifically for real Stripe events.
    
    This endpoint is public but strictly protected by Stripe's HMAC signature
    verification using the `STRIPE_WEBHOOK_SECRET`. It processes events like
    `payment_intent.succeeded` to update the internal settlement engine.
    """
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        if not signature:
            logger.warning("Missing Stripe-Signature header. Rejecting request.")
            raise UAEError(error_code="MISSING_SIGNATURE", message="Missing Stripe-Signature header", status_code=400)
            
        success = handle_stripe_webhook(body, signature)
        
        if not success:
            logger.warning("Failed to verify or process Stripe webhook.")
            raise UAEError(error_code="INVALID_WEBHOOK", message="Failed to verify or process Stripe webhook", status_code=400)
            
        return {"status": "received"}
    except UAEError as e:
        raise e
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to process Stripe webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the webhook.")

@app.post(
    "/proxy/execute",
    response_model=ProxyResponse,
    summary="Execute an MCP/A2A Tool Call",
    response_description="The result of the proxy execution, including settlement and audit details.",
    responses={
        200: {
            "description": "Successful execution",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "injected_credential": True,
                        "x402_settled": True,
                        "transaction_id": "tx_stripe_12345",
                        "audit_id": "adt_9876543210abcdef"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Missing or invalid API key"},
        402: {"description": "Payment Required - Missing or insufficient payment amount"},
        403: {"description": "Forbidden - Insufficient scopes or missing credential"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error"}
    }
)
async def proxy_execute(request: ProxyRequest):
    """
    Execute a tool call through the secure proxy.
    Handles credential injection, scope validation, and x402 micropayment settlement.
    
    **x402 Micropayments & Vertical Credentials:**
    - If the `tool_call` specifies a `required_payment`, the proxy's native x402 middleware
      will intercept the request. If `payment_amount` is insufficient, it returns a `402 Payment Required` error.
    - Agents can retry failed x402 calls by providing a valid `payment_proof` (transaction ID)
      from a previous successful settlement to avoid double-charging.
    - The Identity Engine automatically validates requested scopes against loaded Vertical Credential Packs
      (e.g., the Finance pack for `stripe_live`, `plaid_link`, `bank_api`).
    
    This is the unbreakable foundation that every future module (identity engine, 
    settlement, A2A routing, compliance) will extend. It is fully **Model Context Protocol (MCP)** 
    and **Agent-to-Agent (A2A)** compatible.
    
    **Example Request (Downstream HTTP with x402):**
    ```json
    {
      "agent_id": "agent_123",
      "tool_call": {
        "url": "https://api.example.com/data",
        "method": "POST",
        "payload": {"query": "test"},
        "required_payment": 0.50
      },
      "credential_type": "stripe_live",
      "payment_amount": 0.50
    }
    ```
    
    **Example Request (Paid Discovery):**
    ```json
    {
      "agent_id": "agent_123",
      "tool_call": {
        "action": "discover",
        "required_payment": 0.01
      },
      "credential_type": "stripe_live",
      "payment_amount": 0.01
    }
    ```
    """
    try:
        logger.info(f"Received proxy request from {request.agent_id}")
        response = await execute_proxy_request(request)
        return response
    except RateLimitExceeded as e:
        logger.warning(f"Rate limit exceeded for {request.agent_id}: {e.detail}")
        raise HTTPException(
            status_code=429,
            detail=e.detail,
            headers={"Retry-After": str(e.retry_after)}
        )
    except UAEError as e:
        raise e
    except Exception as e:
        # Catch unexpected errors and return a consistent, user-friendly 500 response
        logger.error(f"Proxy execution failed for {request.agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal server error occurred while processing the proxy request. Please try again later."
        )

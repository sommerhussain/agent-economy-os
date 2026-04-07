"""
Universal Agent Economy OS - Authentication Middleware

This module provides the v0 security layer for the proxy. It enforces API key
authentication on protected routes using either the 'Authorization: Bearer' or
'X-API-Key' headers. It will compound into a full Identity Engine with JWT
validation and scopes in the future.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.config import settings

logger = logging.getLogger(__name__)

# List of paths that do not require authentication
PUBLIC_PATHS = ["/", "/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/webhooks/payment"]

async def api_key_middleware(request: Request, call_next):
    """
    Middleware to enforce API key authentication on protected routes.
    Supports both 'Authorization: Bearer <key>' and 'X-API-Key: <key>' headers.
    
    This is a foundational v0 security layer. In the future, this will compound
    into a full Identity Engine with JWT validation, scopes, and agent-level permissions.
    """
    # Allow public endpoints to pass through without authentication
    if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    # Extract the key from either the Authorization header or the X-API-Key header
    api_key = None
    
    # Check X-API-Key header first
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key:
        api_key = x_api_key
    else:
        # Fallback to Authorization: Bearer
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header.split(" ")[1]

    if not api_key:
        logger.warning(f"Unauthorized access attempt to {request.url.path}: Missing API key")
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication credentials were not provided. Please use the 'Authorization: Bearer <key>' or 'X-API-Key: <key>' header."}
        )

    if api_key != settings.API_KEY:
        logger.warning(f"Unauthorized access attempt to {request.url.path}: Invalid API key")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key provided."}
        )

    # If authentication is successful, proceed to the next middleware/endpoint
    return await call_next(request)

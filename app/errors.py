"""
Universal Agent Economy OS - Structured Error Reporting

This module defines the base UAEError and specific exception subclasses.
It provides a foundation for structured error reporting and observability
(e.g., OpenTelemetry, Sentry) in future iterations.
"""
from typing import Optional, Dict, Any

class UAEError(Exception):
    """Base exception for all Universal Agent Economy OS errors."""
    def __init__(self, message: str, error_code: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class InsufficientScopesError(UAEError):
    """Raised when an agent lacks the required scopes for an operation."""
    def __init__(self, required_scopes: list, message: str = "Insufficient permissions or missing credential."):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_SCOPES",
            status_code=403,
            details={"required_scopes": required_scopes}
        )

class PaymentFailedError(UAEError):
    """Raised when a payment settlement fails."""
    def __init__(self, message: str = "Payment settlement failed."):
        super().__init__(
            message=message,
            error_code="PAYMENT_FAILED",
            status_code=402
        )

class InvalidA2ARouteError(UAEError):
    """Raised when an A2A routing target is invalid or unreachable."""
    def __init__(self, target_agent_id: str, message: str = "Invalid A2A routing target."):
        super().__init__(
            message=message,
            error_code="INVALID_A2A_ROUTE",
            status_code=400,
            details={"target_agent_id": target_agent_id}
        )

class AgentNotFoundError(UAEError):
    """Raised when an agent cannot be found in the identity engine."""
    def __init__(self, agent_id: str, message: str = "Agent not found."):
        super().__init__(
            message=message,
            error_code="AGENT_NOT_FOUND",
            status_code=404,
            details={"agent_id": agent_id}
        )

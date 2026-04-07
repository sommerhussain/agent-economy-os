"""
Universal Agent Economy OS - Audit Logging

This module provides the v0 compliance logging layer. It generates unique
audit trail IDs for transactions and logs key details (agent_id, credential_type,
payment_amount, success). In the future, this will write immutably to a ledger
or external audit service.
"""
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_audit_id() -> str:
    """
    Generates a unique audit trail ID for a transaction.
    """
    return f"adt_{uuid.uuid4().hex}"

def log_request(
    audit_id: str,
    agent_id: str,
    credential_type: str,
    payment_amount: Optional[float],
    success: bool
) -> None:
    """
    Logs the key details of a proxy request for compliance and auditing.
    In the future, this will write immutably to a ledger, database, or external audit service.
    """
    log_data = {
        "audit_id": audit_id,
        "agent_id": agent_id,
        "credential_type": credential_type,
        "payment_amount": payment_amount,
        "success": success
    }
    logger.info(f"Audit Log: {log_data}")

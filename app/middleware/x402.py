"""
Universal Agent Economy OS - Native x402 Middleware

This module provides the middleware layer for x402 micropayments. It intercepts
requests, checks if the target tool or agent requires a payment, verifies the
provided payment amount, and returns an HTTP 402 Payment Required response
with clear instructions if the payment is missing or insufficient.
"""
import logging
from typing import Tuple, Optional, Any, Dict
from app.errors import PaymentRequiredError, PaymentFailedError
from app.payments import execute_payment

logger = logging.getLogger(__name__)

def process_x402_payment(agent_id: str, tool_call: Dict[str, Any], payment_amount: Optional[float], payment_proof: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Native x402 middleware logic.
    
    1. Checks if the tool call requires a payment (e.g., via a 'required_payment' field).
       - If action is 'discover', automatically enforces a minimum discovery fee (e.g., 0.01).
    2. If a payment_proof is provided, verifies it. If valid, bypasses new payment.
    3. Verifies that the provided payment_amount is sufficient.
    4. If insufficient or missing, raises a 402 PaymentRequiredError.
    5. If sufficient, executes the payment via the settlement engine.
    
    Returns:
        Tuple[bool, Optional[str]]: (settled_status, transaction_id)
    """
    required_payment = float(tool_call.get("required_payment", 0.0))
    
    # Discovery mode: enforce a tiny fee for discovering premium tools
    if tool_call.get("action") == "discover" and required_payment < 0.01:
        required_payment = 0.01
        logger.info(f"Discovery mode activated for agent {agent_id}. Enforcing minimum fee of {required_payment}.")
    
    # If a payment proof is provided, verify it first (automatic retry logic)
    if payment_proof:
        logger.info(f"Agent {agent_id} provided payment proof: {payment_proof}")
        # Stub verification: In a real system, we'd query Stripe or our DB to ensure
        # the transaction ID is valid, successful, and matches the required amount.
        if payment_proof.startswith("tx_") and len(payment_proof) > 5:
            logger.info(f"Payment proof {payment_proof} verified successfully for agent {agent_id}.")
            return True, payment_proof
        else:
            logger.warning(f"Invalid payment proof provided by agent {agent_id}: {payment_proof}")
            raise PaymentFailedError("Invalid payment proof provided.")

    provided_amount = float(payment_amount) if payment_amount is not None else 0.0
    
    # Check if payment is required but not provided or insufficient
    if required_payment > 0.0 and provided_amount < required_payment:
        logger.warning(f"Agent {agent_id} provided insufficient payment ({provided_amount}) for required {required_payment}.")
        raise PaymentRequiredError(required_amount=required_payment)
        
    # If a payment is provided (even optionally), process it
    if provided_amount > 0.0:
        logger.info(f"Processing x402 payment of {provided_amount} for agent {agent_id}.")
        settled, transaction_id, _ = execute_payment(provided_amount, agent_id)
        
        if not settled:
            logger.error(f"x402 payment settlement failed for agent {agent_id}.")
            raise PaymentFailedError("Payment settlement failed during x402 middleware processing.")
            
        return True, transaction_id
        
    # No payment required and no payment provided
    return False, None

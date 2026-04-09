"""
Universal Agent Economy OS - Payment Gateway Engine

This module handles the settlement of x402 micropayments. It provides a real
Stripe integration alongside a robust simulation stub for local development.
"""
import uuid
import hmac
import hashlib
import logging
import stripe
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

def simulate_payment(payment_amount: float, agent_id: str) -> Tuple[bool, Optional[str], float]:
    """
    Simulates a payment for testing and local development.
    """
    transaction_id = f"tx_sim_{uuid.uuid4().hex}"
    logger.info(f"Processed simulated payment of {payment_amount} for agent {agent_id}. TX: {transaction_id}")
    return True, transaction_id, payment_amount

def process_payment(payment_amount: float, agent_id: str) -> Tuple[bool, Optional[str], float]:
    """
    Processes a real payment using the Stripe SDK.
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.error("STRIPE_SECRET_KEY is not configured for live mode.")
        return False, None, payment_amount
        
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        # Convert amount to cents for Stripe
        amount_cents = int(payment_amount * 100)
        
        # Using PaymentIntent for modern Stripe integration
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            description=f"x402 micropayment for agent {agent_id}",
            payment_method="pm_card_visa", # Hardcoded for demonstration, in a real system this would be passed
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
        )
        logger.info(f"Processed real Stripe payment of {payment_amount} for agent {agent_id}. TX: {intent.id}")
        return True, intent.id, payment_amount
    except stripe.StripeError as e:
        logger.error(f"Stripe payment failed for agent {agent_id}: {e}")
        return False, None, payment_amount
    except Exception as e:
        logger.error(f"Unexpected error during Stripe payment for agent {agent_id}: {e}")
        return False, None, payment_amount

def execute_payment(payment_amount: float, agent_id: str) -> Tuple[bool, Optional[str], float]:
    """
    Routes the payment to either the real Stripe integration or the simulation
    based on the STRIPE_MODE configuration.
    """
    if payment_amount <= 0:
        logger.warning(f"Invalid payment amount: {payment_amount} for agent {agent_id}. Must be greater than 0.")
        return False, None, payment_amount

    if settings.STRIPE_MODE == "live":
        return process_payment(payment_amount, agent_id)
    else:
        return simulate_payment(payment_amount, agent_id)

class PaymentWebhookPayload(BaseModel):
    """
    Payload for incoming payment webhook confirmations.
    """
    transaction_id: str = Field(..., description="Unique transaction ID")
    status: str = Field(..., description="Payment status (e.g., 'success', 'failed')")
    amount: float = Field(..., description="Payment amount settled")
    agent_id: str = Field(..., description="Agent ID associated with the payment")

def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verifies the HMAC signature of an incoming webhook using the STRIPE_WEBHOOK_SECRET.
    """
    secret = settings.STRIPE_WEBHOOK_SECRET or settings.WEBHOOK_SECRET
    if not secret:
        logger.warning("Webhook secret is not configured. Rejecting webhook.")
        return False
        
    if not signature_header:
        logger.warning("Missing signature header in webhook request.")
        return False

    # Compute expected HMAC SHA256 signature
    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature_header)

async def process_payment_webhook(payload: PaymentWebhookPayload) -> bool:
    """
    Processes the verified payment webhook payload.
    Updates internal metering/audit systems as necessary.
    """
    logger.info(f"Processing payment webhook for TX: {payload.transaction_id}, Status: {payload.status}")
    
    if payload.status == "success":
        # Stub: In a real system, this would update the transaction record in the DB
        # and perhaps trigger an async event for the agent.
        logger.info(f"Payment {payload.transaction_id} for agent {payload.agent_id} confirmed successful.")
        return True
    else:
        logger.warning(f"Payment {payload.transaction_id} for agent {payload.agent_id} reported status: {payload.status}")
        return False

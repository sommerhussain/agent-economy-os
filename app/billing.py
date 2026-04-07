"""
Universal Agent Economy OS - Billing Engine

This module handles usage-based billing calculation and invoice generation.
It acts as a stub for real invoice PDF generation and Stripe invoicing (Day 23-24).
"""
import uuid
import logging
import threading
from typing import List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.metering import get_usage_stats
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory store for generated invoices (stub for DB)
_invoice_store: List['Invoice'] = []
_invoice_lock = threading.Lock()

class Invoice(BaseModel):
    """
    Invoice payload representing usage-based billing for an agent.
    """
    invoice_id: str = Field(..., description="Unique invoice identifier", examples=["inv_12345abcde"])
    agent_id: str = Field(..., description="Agent identifier being billed", examples=["agent_123"])
    total_calls: int = Field(..., description="Total number of API calls made", examples=[150])
    total_payment_volume: float = Field(..., description="Total x402 payment volume processed", examples=[25.50])
    applied_rate: float = Field(..., description="Rate applied per API call", examples=[0.01])
    amount_due: float = Field(..., description="Total amount due for this invoice", examples=[1.50])
    status: str = Field("draft", description="Invoice status (draft, open, paid, void)", examples=["draft"])
    generated_at: str = Field(..., description="ISO 8601 timestamp of invoice generation")

def calculate_usage_invoice(agent_id: str) -> Invoice:
    """
    Calculates usage-based billing for a given agent and generates a draft invoice.
    Uses the configured BILLING_RATE_PER_CALL.
    """
    logger.info(f"Calculating usage invoice for agent: {agent_id}")
    
    # Fetch current usage stats from the metering engine
    stats = get_usage_stats(agent_id)
    total_calls = stats.get("total_calls", 0)
    total_volume = stats.get("total_payment_amount", 0.0)
    
    # Calculate amount due based on flat rate per call
    rate = settings.BILLING_RATE_PER_CALL
    amount_due = total_calls * rate
    
    invoice_id = f"inv_{uuid.uuid4().hex}"
    
    logger.info(f"Generated draft invoice {invoice_id} for agent {agent_id}. Total calls: {total_calls}, Amount Due: {amount_due}")
    
    invoice = Invoice(
        invoice_id=invoice_id,
        agent_id=agent_id,
        total_calls=total_calls,
        total_payment_volume=total_volume,
        applied_rate=rate,
        amount_due=amount_due,
        status="draft",
        generated_at=datetime.now(timezone.utc).isoformat()
    )
    
    with _invoice_lock:
        _invoice_store.append(invoice)
        
    return invoice

def get_recent_invoices() -> List[Invoice]:
    """
    Returns the most recently generated invoices.
    """
    from app.config import settings
    limit = settings.DASHBOARD_RECENT_INVOICES_LIMIT
    
    with _invoice_lock:
        # Sort by generated_at descending (latest first)
        sorted_invoices = sorted(_invoice_store, key=lambda i: i.generated_at, reverse=True)
        return sorted_invoices[:limit]

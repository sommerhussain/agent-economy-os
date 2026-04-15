"""
Universal Agent Economy OS - Usage Limits and Pricing Tiers

This module provides logic to enforce usage limits based on pricing tiers.
It reuses the existing metering data to determine if an agent has exceeded
their allowed API calls.
"""
import logging
from typing import Dict, Any
from app.config import settings
from app.metering import get_usage_stats
from app.errors import PaymentRequiredError

logger = logging.getLogger(__name__)

def check_usage_limits(agent_id: str) -> None:
    """
    Checks if the agent has exceeded their usage limits based on their tier.
    For v0, we assume all agents are on the FREE_TIER unless they have a
    specific override (which could be added to identity metadata later).
    
    Raises:
        PaymentRequiredError: If the agent has exceeded their allowed limit.
    """
    stats = get_usage_stats(agent_id)
    total_calls = stats.get("total_calls", 0)
    
    # In a future iteration, we would fetch the agent's actual tier from the Identity Engine
    # For now, we enforce the FREE_TIER_LIMIT for everyone to start generating revenue
    limit = settings.FREE_TIER_LIMIT
    
    if total_calls >= limit:
        logger.warning(f"Agent {agent_id} exceeded usage limit ({total_calls}/{limit} calls).")
        raise PaymentRequiredError(
            required_amount=10.0, # Example amount to upgrade to PRO
            message=f"Usage limit exceeded. You have made {total_calls} calls (limit: {limit}). Please upgrade your tier."
        )

def get_tier_status(agent_id: str) -> Dict[str, Any]:
    """
    Returns the current usage vs limits for the given agent, including projected costs.
    """
    stats = get_usage_stats(agent_id)
    total_calls = stats.get("total_calls", 0)
    limit = settings.FREE_TIER_LIMIT
    projected_cost = total_calls * settings.BILLING_RATE_PER_CALL
    
    return {
        "tier": "free",
        "total_calls": total_calls,
        "limit": limit,
        "remaining": max(0, limit - total_calls),
        "exceeded": total_calls >= limit,
        "projected_cost": round(projected_cost, 4)
    }

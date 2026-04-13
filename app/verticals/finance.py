"""
Universal Agent Economy OS - Finance Vertical Credential Pack

This module provides the Finance vertical credential pack, which defines
standardized financial credentials (e.g., Stripe, Plaid, Bank APIs) and
their allowed scopes for secure x402 micropayments and ledger access.
"""
from app.verticals.base import CredentialPack, CredentialDefinition

FinanceCredentialPack = CredentialPack(
    pack_id="finance",
    name="Finance",
    description="Core financial credentials for payments, banking, and ledger access.",
    credentials={
        "stripe_live": CredentialDefinition(
            name="Stripe Live Key",
            description="Live Stripe API key for processing real payments.",
            allowed_scopes=["payment:read", "payment:write", "refund:write"]
        ),
        "plaid_link": CredentialDefinition(
            name="Plaid Link Token",
            description="Plaid token for linking bank accounts.",
            allowed_scopes=["account:read", "transaction:read"]
        ),
        "bank_api": CredentialDefinition(
            name="Generic Bank API",
            description="Standardized banking API access.",
            allowed_scopes=["balance:read", "transfer:write"]
        )
    }
)

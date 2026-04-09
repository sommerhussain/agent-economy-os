"""
Universal Agent Economy OS - Master Configuration

This module defines the single source of truth for all environment variables
using Pydantic v2 Settings. It compounds perfectly into Docker, auth,
metering, identity, and payments.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Master configuration object for the Universal Agent Economy OS.
    This serves as the single source of truth for all environment variables,
    compounding perfectly into Docker, auth, metering, identity, and payments.
    """
    # Temporary default for initial Railway deployment. Make required in production.
    API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    ALLOWED_ORIGINS: List[str] = ["*"]
    STRIPE_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_MODE: str = "simulation"
    LIGHTNING_ENABLED: bool = False
    BILLING_RATE_PER_CALL: float = 0.01
    # Temporary default for initial Railway deployment. Make required in production.
    WEBHOOK_SECRET: str = ""
    REDIS_URL: str = ""  # Redis connection string (e.g., redis://localhost:6379). Leave empty for in-memory fallback.
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    ANALYTICS_ACTIVE_WINDOW_SECONDS: int = 86400
    ANALYTICS_MAX_RECENT_EVENTS: int = 50
    DASHBOARD_RECENT_INVOICES_LIMIT: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

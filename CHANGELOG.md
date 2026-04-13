# Changelog

All notable changes to the Universal Agent Economy OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-04-13

### Added
- **Vertical Credential Packs**: Introduced a modular `app/verticals` system to define standardized credential types and scopes.
- **Finance Pack**: Added `FinanceCredentialPack` supporting `stripe_live`, `plaid_link`, and `bank_api` credentials with default scopes.
- **Identity Engine Validation**: Automatic scope validation and defaulting during credential rotation based on loaded vertical packs.
- **Verticals Endpoint**: New `GET /verticals` endpoint to list all available credential packs and their definitions.

## [0.1.1] - 2026-04-09

### Added
- **Stripe Webhook Integration**: Secure handling of real Stripe events (`payment_intent.succeeded`, `payment_intent.payment_failed`) via `/webhooks/stripe` using HMAC signature verification.
- **SDK Enhancements**: Python SDK updated to fully expose the revenue stack (`execute_payment`, `get_stats`, `get_invoice`).
- **Redis-Ready Infrastructure**: Upgraded rate limiting, caching, and usage metering to be fully Redis-compatible for horizontal scaling, with seamless in-memory fallbacks.

## [0.1.0] - 2026-04-06

### Added
- **Core Proxy Engine**: A high-performance, strictly typed FastAPI gateway (`/proxy/execute`) for secure credential injection and downstream execution.
- **Identity Engine**: Supabase integration for agent registration, credential issuance, rotation, and cryptographic scope validation (`/agents/register`, `/credentials/rotate`, `/agents/{agent_id}/scopes`).
- **Settlement Engine**: x402 micropayment handling stub, usage-based billing invoice generation (`/billing/invoice/{agent_id}`), and HMAC-secured Stripe/Lightning webhook verification (`/webhooks/payment`).
- **A2A Routing**: Intelligent Agent-to-Agent routing engine (`/a2a/route`) for direct agent communication.
- **Python SDK**: An official, async-first Python client (`UAEOSClient`) with connection pooling, exponential backoff retries, and structured error handling.
- **Usage Analytics**: Thread-safe in-memory usage tracking, recent activity logging, and a global `/stats` dashboard.
- **Traffic Control**: Redis-ready rate limiting architecture enforcing limits per agent.
- **Caching**: Redis-ready identity caching layer for credentials and scopes.
- **Security**: API Key authentication middleware, CORS configuration, custom security headers, and structured error reporting (`UAEError`).
- **Compliance Packs**: Comprehensive audit logging with unique `adt_` transaction IDs.
- **Infrastructure**: Centralized Pydantic Settings (`app/config.py`), Dockerized deployment setup, and one-click Railway configuration (`railway.toml`).
- **Testing**: A comprehensive test suite with 82 integration and unit tests achieving 100% code coverage.

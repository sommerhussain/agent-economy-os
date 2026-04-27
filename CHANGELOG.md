# Changelog

All notable changes to the Universal Agent Economy OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.9] - 2026-04-27

### Added
- **Self-Healing Mechanics**: Added `auto_rotate_agent_credentials` stub to the Identity Engine, demonstrating zero-touch maintenance for high-frequency credential rotation in regulated industries.
- **Infrastructure-as-Code**: Introduced a complete Terraform foundation (`deploy/terraform/`) for one-command enterprise deployment to AWS/GCP/Azure.
- **Enterprise Documentation**: Expanded the `README.md` with a "For Acquirers / New Maintainers" section, highlighting the asset's multi-monopoly surface, revenue engine, and handover readiness.
- **Codebase Audit**: Removed personal references and polished metadata (`server.json`, `LICENSE`, `.well-known` files) to use generic, enterprise-friendly identifiers.
- **Vertical Packs**: Added Healthcare, Logistics, and Marketing vertical credential packs with auditor-ready export stubs and least-privilege enforcement.

## [0.1.8] - 2026-04-25

### Added
- **x402 Middleware Enhancements**: Added response-embedded `recommendation_metadata` to actively propagate premium tools and vertical packs.
- **Compliance Pack Upgrades**: Enhanced `export_audit_report` with time ranges and volume tracking, and added `soc2_compliance_auditor` credential.
- **Discovery Optimization**: Enriched `.well-known/agent-card.json` and `.well-known/mcp.json` with semantic keywords, tags, and capabilities.
- **Pricing Dashboard & Projections**: Upgraded `/stats` and `app/analytics.py` to include 7-day, 30-day, and annual projected revenue, plus structured `AgentTierStatus`.
- **Weekly Polish**: Version bump to 0.1.8 and endpoint refinements.

## [0.1.7] - 2026-04-17

### Added
- **Compliance & Governance Pack Enhancements**: Added auditor-ready export features and `audit_report_generator` credential.
- **Strengthened Paid Discovery**: Expanded `action="discover"` loop with premium Compliance and Legal tool examples.
- **Pricing Dashboard Improvements**: Added `projected_cost` and `tier_recommendation` to agent tier status.
- **Expanded On-Chain Identity**: Added `smart_contract_execution`, `dao_governance_token`, and `cross_chain_bridge` to the ERC-8004 On-Chain pack.
- **Daily Revenue Summary**: Added `daily_revenue_summary` tracking to the Analytics Engine, exposed via `/stats` and `/health`.
- **SDK & Documentation Polish**: Updated Python SDK and `README.md` with comprehensive examples for all 6 vertical packs and the enhanced pricing dashboard.

## [0.1.6] - 2026-04-07

### Added
- **Legal Vertical Pack**: Added the `LegalCredentialPack` with credentials for legal contracts, IP registries, and e-signatures.
- **Enhanced On-Chain Identity**: Expanded ERC-8004 identity stub to include SIWE sessions and verifiable credentials.
- **Pricing Dashboard Improvements**: Added projected costs to the `/stats` dashboard and agent tier status.
- **Paid Discovery Examples**: Enhanced the paid discovery loop (`action="discover"`) with compliance and legal tool examples.
- **Documentation & SDK Polish**: Updated `README.md` and Python SDK with comprehensive examples for paid discovery and the new vertical packs.

## [0.1.5] - 2026-04-16

### Added
- **Final Weekly Polish**: Revenue monitoring setup, optimized discovery metadata, and preparation for the next phase.
- **On-Chain Identity Stub**: Added basic ERC-8004 on-chain identity stub (`app/identity/onchain.py`) to future-proof for hybrid fiat/on-chain credentials.
- **Compute & Data Vertical Packs**: Introduced `ComputeCredentialPack` and `DataCredentialPack` for AI model inference, cloud compute, and data access.
- **Paid Discovery**: Extended x402 middleware with a special `discover` action, allowing agents to pay a tiny fee to discover premium tools.
- **Usage Limits & Pricing Dashboard**: Enhanced the `/stats` dashboard to clearly display pricing tier information, usage, and remaining quota per agent.

## [0.1.4] - 2026-04-15

### Added
- **Final Polish & Release Prep**: Comprehensive audit, documentation updates, and release preparation for v0.1.4.
- **Discovery Metadata**: Added standard MCP/A2A discovery files (`.well-known/agent-card.json`, `.well-known/mcp.json`).
- **x402 Retries**: Full support for `payment_proof` in the native x402 middleware for automatic retries without double-charging.
- **Vertical Credential Packs**: Integrated Finance pack (`stripe_live`, `plaid_link`, `bank_api`) with automatic scope validation.

## [0.1.3] - 2026-04-14

### Added
- **x402 & Vertical Documentation**: Added comprehensive documentation to `README.md` detailing the native x402 middleware, payment retries (`payment_proof`), and Vertical Credential Packs (Finance examples).
- **SDK Enhancements**: Added `get_vertical_packs()` method to the Python SDK (`UAEOSClient`) to dynamically fetch available credential packs.
- **OpenAPI Improvements**: Enhanced docstrings and OpenAPI schemas in `app/main.py` for `/proxy/execute` (detailing x402 behaviour) and `/verticals`.

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

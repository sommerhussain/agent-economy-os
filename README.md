<!--
================================================================================
RELEASE CHECKLIST (v0.1.0)
================================================================================
After pushing to GitHub:
1. Go to your repository's "Releases" tab.
2. Click "Draft a new release".
3. Create a new tag: "v0.1.0".
4. Title the release: "v0.1.0 - Foundation Proxy".
5. Copy the "v0.1 Release Notes" section below into the release description.
6. Click "Publish release".
7. Connect your repo to Railway (or Vercel) and verify the live deployment.
8. (Optional) Publish the SDK to PyPI using `python -m build` and `twine upload dist/*`.
================================================================================
-->

# Universal Agent Economy OS (UAE OS)

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Version](https://img.shields.io/badge/version-v0.1.4-orange)

The **Universal Agent Economy OS** is a foundational, MCP/A2A-native core platform designed to power the exploding agentic sub-economy. It begins as a secure credential injection and x402 micropayment proxy, compounding daily into a full multi-monopoly empire (identity engine, payments, settlement, compliance packs, vertical marketplaces).

This v0 proxy skeleton is the unbreakable foundation that every future module will extend. It is fully **Model Context Protocol (MCP)** and **Agent-to-Agent (A2A)** compatible, allowing autonomous agents to securely discover, authenticate, and pay each other without human intervention.

---

## Quick Start with Python SDK

The easiest way to interact with the UAE OS is via the official Python SDK. It provides robust connection pooling, automatic exponential backoff retries for transient errors (429s, 5xxs), and structured exception handling that maps directly to the `UAEError` system.

### 1. Installation
Install the SDK directly from the repository root:
```bash
pip install -e .
```

### 2. Basic Usage & Error Handling
```python
import asyncio
from sdk.uaeos import UAEOSClient
from sdk.uaeos.client import RateLimitError, AuthError, InsufficientScopesError, APIError

async def main():
    # Initialize the client with your API key (uses async context manager for connection pooling)
    # The client automatically retries transient errors (max_retries=3 by default)
    async with UAEOSClient(api_key="sk_test_1234567890abcdef", base_url="http://127.0.0.1:8000") as client:
        try:
            # 1. Register a new agent in the Identity Engine
            agent = await client.register_agent(
                agent_id="agent_sdk_1", 
                name="SDK Test Agent", 
                metadata={"version": "1.0"}
            )
            print("Registered:", agent)
            
            # 2. Rotate/Issue a credential with cryptographic scopes
            cred = await client.rotate_credential(
                agent_id="agent_sdk_1",
                credential_type="stripe_live",
                new_secret_data={"api_key": "sk_live_new123"},
                expires_in_days=30
            )
            print("Credential Rotated:", cred)
            
            # 3. Execute an MCP/A2A tool call with x402 micropayment
            result = await client.execute(
                agent_id="agent_sdk_1",
                tool_call={
                    "target_agent_id": "agent_target_2",
                    "action": "process_data",
                    "payload": {"hello": "world"},
                    "required_scopes": ["read"]
                },
                credential_type="stripe_live",
                payment_amount=1.50
            )
            print("Execution Result:", result)
            
            # 4. Execute a direct A2A payment (no downstream HTTP call)
            payment_result = await client.execute_payment(
                agent_id="agent_sdk_1",
                payment_amount=5.00,
                target_agent_id="agent_target_3",
                action="data_purchase"
            )
            print("Payment Result:", payment_result)
            
            # 5. Get Usage Stats from the Analytics Engine
            stats = await client.get_stats()
            print("Global Stats:", stats)
            
            # 6. Generate a usage-based invoice for the agent
            invoice = await client.get_invoice(agent_id="agent_sdk_1")
            print("Generated Invoice:", invoice)
            
            # 7. List available Vertical Credential Packs
            verticals = await client.get_vertical_packs()
            print("Available Verticals:", verticals)
            
        except RateLimitError as e:
            # Raised if the agent exceeds the rate limit and max_retries are exhausted
            print(f"Rate limited! Retry after {e.retry_after} seconds. Request ID: {e.request_id}")
        except InsufficientScopesError as e:
            # Raised if the agent lacks the required scopes for the credential
            print(f"Permission denied: {e.message}")
        except AuthError:
            # Raised for 401 Unauthorized
            print("Invalid API Key!")
        except APIError as e:
            # Catch-all for other 4xx/5xx errors or network issues
            print(f"API Error ({e.status_code}): {e.message}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## x402 Micropayments & Settlement

The Universal Agent Economy OS features a native x402 middleware that intercepts tool calls requiring payment. This allows agents to autonomously negotiate and settle micropayments before executing downstream requests.

### How it Works
1. **Required Payment**: If an agent requests a tool call that specifies a `required_payment` (e.g., `0.50`), the x402 middleware checks the provided `payment_amount`.
2. **Payment Required (402)**: If the `payment_amount` is missing or insufficient, the proxy immediately returns an HTTP `402 Payment Required` error, detailing the required amount.
3. **Settlement**: If sufficient funds are provided, the proxy uses the Settlement Engine (e.g., Stripe) to process the payment.
4. **Retries & Payment Proof**: To prevent double-charging on transient failures (like a network timeout after payment), agents can submit a `payment_proof` (the `transaction_id` from a previous successful settlement). The middleware verifies this proof and bypasses the charge, allowing the tool call to proceed.

### Example: x402 with Python SDK
```python
# 1. Attempt a tool call that requires payment
try:
    await client.execute(
        agent_id="agent_1",
        tool_call={"url": "https://api.example.com/premium", "required_payment": 1.0},
        credential_type="stripe_live"
    )
except APIError as e:
    if e.status_code == 402:
        print("Payment required! Retrying with funds...")
        
        # 2. Retry with sufficient payment
        result = await client.execute(
            agent_id="agent_1",
            tool_call={"url": "https://api.example.com/premium", "required_payment": 1.0},
            credential_type="stripe_live",
            payment_amount=1.0
        )
        
        # Save the transaction ID for future retries
        tx_id = result.get("transaction_id")
        
        # 3. Retry a failed downstream call using payment_proof
        retry_result = await client.execute(
            agent_id="agent_1",
            tool_call={"url": "https://api.example.com/premium", "required_payment": 1.0},
            credential_type="stripe_live",
            payment_proof=tx_id
        )
```

---

## Vertical Credential Packs

The Universal Agent Economy OS supports modular "Vertical Credential Packs". These packs define standardized credential types and cryptographic scopes for specific industries (e.g., Finance, Social, Cloud).

### Using the Finance Pack
The `FinanceCredentialPack` is built-in and automatically loaded. It provides standardized definitions for:
- `stripe_live` (Scopes: `payment:read`, `payment:write`, `refund:write`)
- `plaid_link` (Scopes: `account:read`, `transaction:read`)
- `bank_api` (Scopes: `balance:read`, `transfer:write`)

When rotating credentials for these types, the Identity Engine will automatically validate requested scopes against the pack's allowed scopes. If no scopes are provided, it defaults to granting all allowed scopes for that credential type.

### Example: Rotating a Vertical Credential
```python
# Rotate a Plaid credential. The Identity Engine automatically
# assigns the default scopes: ["account:read", "transaction:read"]
await client.rotate_credential(
    agent_id="agent_1",
    credential_type="plaid_link",
    new_secret_data={"access_token": "access-sandbox-123"}
)

# Execute a tool call requiring the 'transaction:read' scope
await client.execute(
    agent_id="agent_1",
    tool_call={
        "url": "https://sandbox.plaid.com/transactions/get",
        "required_scopes": ["transaction:read"]
    },
    credential_type="plaid_link"
)
```

**View Available Verticals:**
```bash
curl -X GET "http://127.0.0.1:8000/verticals" \
     -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Agent Discovery & MCP Manifest

The UAE OS is fully discoverable by other agents and MCP clients. It serves standard discovery metadata at the following public endpoints:

- **Agent Card (`/.well-known/agent-card.json`)**: Provides A2A discovery metadata, including the agent's name, description, capabilities (like x402 micropayments), and available endpoints.
- **MCP Manifest (`/.well-known/mcp.json`)**: Provides the official Model Context Protocol server manifest, allowing MCP clients to dynamically connect to the proxy's execute endpoint.

These endpoints are public and do not require an API key.

---

## v0.1 Release Notes

Welcome to the foundational release of the Universal Agent Economy OS! Over the past 30 days, we have built a highly modular, production-ready proxy skeleton that acts as the core router for the MCP/A2A network.

**Features in v0.1.0:**
- **FastAPI + Pydantic v2 Core**: Strictly typed, high-performance API gateway.
- **Identity Engine**: Supabase integration for secure credential lookup, injection, rotation, and cryptographic scope validation.
- **Settlement Engine**: x402 micropayment handling, Stripe/Lightning webhook verification, and usage-based billing invoice generation.
- **A2A Routing**: Intelligent Agent-to-Agent routing stub alongside downstream execution (`httpx`).
- **Compliance Packs**: Audit logging and unique `adt_` ID generation.
- **Traffic Control**: Redis-ready rate limiting (10 req/min) with proper 429 responses.
- **Caching**: Redis-ready identity caching layer for credentials and scopes.
- **Security**: API Key authentication (`Authorization: Bearer` and `X-API-Key`), CORS middleware, custom security headers, and structured error reporting (`UAEError`).
- **Usage Analytics Dashboard**: Thread-safe in-memory usage tracking, recent activity logging, and a global `/stats` dashboard.
- **Python SDK**: An official, async-first Python client (`UAEOSClient`) with connection pooling, exponential backoff retries, and structured error handling.
- **Configuration**: Centralized Pydantic Settings (`app/config.py`) as the single source of truth.
- **Deployment Ready**: Dockerized and optimized for one-click Railway deployment.
- **100% Test Coverage**: Fully mocked, comprehensive test suite with 82 integration tests.

---

## Quick Start (Local Server)

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Copy `.env.example` to `.env` and fill in your Supabase details (optional for local simulation).
   ```bash
   cp .env.example .env
   ```

3. **Run the Server**
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/docs` for the interactive Swagger UI.

4. **Run Tests**
   ```bash
   pytest -v
   ```

---

## Quick Start (Docker)

To run the proxy in an isolated container:

1. **Build the Image**
   ```bash
   docker build -t uae-os-proxy .
   ```

2. **Run the Container**
   ```bash
   docker run -p 8000:8000 --env-file .env uae-os-proxy
   ```

---

## Environment Variables

The application is configured entirely via environment variables (managed by `app/config.py`). See `.env.example` for details.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | *(Required)* | The master API key required to access protected endpoints. |
| `WEBHOOK_SECRET` | *(Required)* | Secret used to verify HMAC signatures on incoming webhooks. |
| `SUPABASE_URL` | `""` | Your Supabase project URL (used for credential lookup). |
| `SUPABASE_KEY` | `""` | Your Supabase anon or service-role key. |
| `ALLOWED_ORIGINS` | `["*"]` | JSON array of allowed CORS origins. |
| `STRIPE_API_KEY` | `""` | Key for real Stripe integration. |
| `LIGHTNING_ENABLED` | `False` | Enable Lightning network micropayments. |
| `BILLING_RATE_PER_CALL` | `0.01` | Flat rate applied per API call for usage-based billing. |
| `RATE_LIMIT_MAX_REQUESTS` | `10` | Maximum number of requests an agent can make within the window. |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds for the rate limit. |
| `REDIS_URL` | `""` | Redis connection string (e.g., `redis://localhost:6379`). Leave empty for in-memory fallback. |

*Note: If Supabase variables are missing, the app gracefully falls back to a simulation mode for testing.*

---

## API Usage Examples (cURL)

The proxy endpoint (`/proxy/execute`) is protected and requires your `API_KEY`. You can authenticate using either the standard `Authorization: Bearer <key>` header or the `X-API-Key: <key>` header.

### 1. Basic Tool Call (No Payment)

**Using cURL (Bearer Token):**
```bash
curl -X POST http://127.0.0.1:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -d '{
    "agent_id": "agent_alpha",
    "tool_call": {
      "url": "https://api.example.com/v1/data",
      "method": "POST",
      "payload": {"query": "test"}
    },
    "credential_type": "stripe_live"
  }'
```

### 2. MCP/A2A Tool Call with x402 Micropayment

To simulate a settlement and route to another agent, include the `payment_amount` and `target_agent_id` fields.

```bash
curl -X POST http://127.0.0.1:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -d '{
    "agent_id": "agent_beta",
    "tool_call": {
      "target_agent_id": "agent_gamma",
      "action": "premium_data_fetch"
    },
    "credential_type": "custom_oauth",
    "payment_amount": 0.50
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "injected_credential": true,
  "x402_settled": true,
  "transaction_id": "tx_a1b2c3d4e5f6",
  "audit_id": "adt_9876543210abcdef"
}
```

---

## Deployment (Zero-Cost / One-Click)

The Dockerfile is optimized for modern PaaS providers. It uses a lightweight Python 3.11 slim image, exposes port 8000, and binds to `0.0.0.0`.

### Deploying to Railway (Recommended)

Railway offers a seamless, one-click deployment experience that reads the included `railway.toml` and `Dockerfile` automatically.

1. **Push to GitHub**: Commit this repository to a GitHub repo.
2. **Connect Railway**: Log into [Railway](https://railway.app/) and click **New Project** -> **Deploy from GitHub repo**.
3. **Select Repo**: Choose your newly pushed repository.
4. **Set Environment Variables**: In your Railway project dashboard, go to the **Variables** tab and add your `API_KEY`, `WEBHOOK_SECRET`, and any optional Supabase/Stripe keys. Ensure you generate strong random strings for the secrets in production.
5. **Deploy**: Railway will automatically detect the `railway.toml` file, build the Docker image, and deploy it.

**Expected Live URL Pattern:**
`https://agent-economy-os-production.up.railway.app`

### Production Monitoring & Verification

Once deployed, you can verify the service is running and monitor its health using the public endpoints. These are the recommended endpoints to use for PaaS health checks:

- **Health Check**: `https://agent-economy-os-production.up.railway.app/health`
  - *Returns basic status, version, and timestamp.*
- **Metrics**: `https://agent-economy-os-production.up.railway.app/metrics`
  - *Returns uptime and total agents metered.*

*Note: Since the current rate limiting and caching are in-memory, ensure your PaaS is configured to run a single instance/replica (which is the default on free tiers) until Redis is fully integrated.*

### Stripe Webhook Setup

To enable real-time settlement tracking for live Stripe payments, configure a webhook in your Stripe Dashboard:

1. Go to **Developers > Webhooks** in the Stripe Dashboard.
2. Click **Add endpoint**.
3. Set the **Endpoint URL** to `https://agent-economy-os-production.up.railway.app/webhooks/stripe`.
4. Select the **Events to send**: `payment_intent.succeeded` and `payment_intent.payment_failed`.
5. Click **Add endpoint**.
6. Reveal the **Signing secret** (starts with `whsec_`) and add it to your Railway environment variables as `STRIPE_WEBHOOK_SECRET`.

---

## Contributing
We welcome contributions! The Universal Agent Economy OS is designed to be the definitive open-source standard for the agentic economy. 

Please ensure that all tests pass (`pytest -v`) and that coverage remains at 100% before submitting a Pull Request. If you are adding a new module, ensure it compounds on the existing architecture without breaking the core proxy execution flow.

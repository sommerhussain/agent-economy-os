"""
Universal Agent Economy OS - Proxy Test Suite

This module contains the full end-to-end test suite for the proxy. It covers
happy paths, edge cases, Pydantic validation errors, 429 Rate Limits,
downstream connection timeouts, and middleware/header checks.
"""
import pytest
import httpx
import os

# Set dummy environment variables for testing before importing the app
os.environ["API_KEY"] = "test_api_key"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""
os.environ["ALLOWED_ORIGINS"] = '["*"]'
os.environ["WEBHOOK_SECRET"] = "test_secret"

from fastapi.testclient import TestClient
from app.main import app
from app.proxy import ProxyRequest, ProxyResponse, execute_proxy_request
from app.payments import execute_payment
from unittest.mock import patch, AsyncMock

client = TestClient(app)

# Helper function to generate authorized headers for tests
def get_auth_headers():
    return {"Authorization": "Bearer test_api_key"}

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_success_with_payment(mock_request):
    """
    Test the /proxy/execute endpoint with a valid payload including a payment amount.
    Expects success, injected credentials, x402 settlement, and a transaction ID.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "method": "POST", "action": "read_data", "params": {"id": 1}},
        "credential_type": "read_only_token",
        "payment_amount": 0.05
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["injected_credential"] is True
    assert data["x402_settled"] is True
    assert "transaction_id" in data
    assert data["transaction_id"].startswith("tx_")
    assert "audit_id" in data
    assert data["audit_id"].startswith("adt_")

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_success_without_payment(mock_request):
    """
    Test the /proxy/execute endpoint with a valid payload but no payment amount.
    Expects success, injected credentials, but no x402 settlement and no transaction ID.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "agent_456",
        "tool_call": {"url": "http://example.com/api", "action": "ping"},
        "credential_type": "basic_auth"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["injected_credential"] is True
    assert data["x402_settled"] is False
    assert data.get("transaction_id") is None
    assert "audit_id" in data

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_invalid_payment(mock_request):
    """
    Test the /proxy/execute endpoint with an invalid payment amount (<= 0).
    Expects x402_settled to be False and transaction_id to be None.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data"},
        "credential_type": "read_only_token",
        "payment_amount": -0.05
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["x402_settled"] is False
    assert data.get("transaction_id") is None

def test_proxy_execute_payment_required():
    """
    Test the /proxy/execute endpoint when the tool call requires a payment
    but none is provided. Expects a 402 Payment Required error.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data", "required_payment": 5.0},
        "credential_type": "read_only_token",
        "payment_amount": 2.0
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 402
    data = response.json()
    assert data["error_code"] == "PAYMENT_REQUIRED"
    assert "payment_instructions" in data["details"]

@patch("app.middleware.x402.execute_payment")
def test_proxy_execute_payment_failed(mock_execute):
    """
    Test the /proxy/execute endpoint when the payment settlement fails.
    Expects a 402 Payment Failed error.
    """
    mock_execute.return_value = (False, None, 5.0)
    
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data", "required_payment": 5.0},
        "credential_type": "read_only_token",
        "payment_amount": 5.0
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 402
    data = response.json()
    assert data["error_code"] == "PAYMENT_FAILED"

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_payment_proof_success(mock_request):
    """
    Test the /proxy/execute endpoint when a valid payment proof is provided.
    Expects success without triggering a new payment.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data", "required_payment": 5.0},
        "credential_type": "read_only_token",
        "payment_proof": "tx_valid_proof_123"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["x402_settled"] is True
    assert data["transaction_id"] == "tx_valid_proof_123"

def test_proxy_execute_payment_proof_failed():
    """
    Test the /proxy/execute endpoint when an invalid payment proof is provided.
    Expects a 402 Payment Failed error.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data", "required_payment": 5.0},
        "credential_type": "read_only_token",
        "payment_proof": "invalid_proof"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 402
    data = response.json()
    assert data["error_code"] == "PAYMENT_FAILED"

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_missing_credentials(mock_request):
    """
    Test the /proxy/execute endpoint when credentials are not found in Supabase.
    The simulation returns None if agent_id doesn't start with 'agent_'.
    Expects success=True (tool execution proceeds) but injected_credential=False.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "unknown_user",
        "tool_call": {"url": "http://example.com/api", "action": "ping"},
        "credential_type": "aws"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["injected_credential"] is False
    assert data["x402_settled"] is False

def test_proxy_execute_missing_url():
    """
    Test the /proxy/execute endpoint when the tool_call payload lacks a URL.
    Expects success=False without attempting an HTTP call.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"action": "ping"}, # No URL provided
        "credential_type": "read_only_token"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_downstream_failure(mock_request):
    """
    Test the /proxy/execute endpoint when the downstream call returns a non-2xx status.
    Expects success=False.
    """
    mock_response = AsyncMock()
    mock_response.is_success = False
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_request.return_value = mock_response

    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api"},
        "credential_type": "read_only_token"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_downstream_connection_error(mock_request):
    """
    Test the /proxy/execute endpoint when the downstream call raises a RequestError.
    Expects success=False.
    """
    mock_request.side_effect = httpx.RequestError("Connection timeout")

    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api"},
        "credential_type": "read_only_token"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

def test_proxy_execute_validation_error():
    """
    Test the /proxy/execute endpoint with missing required fields.
    Expects a 422 Unprocessable Entity error from Pydantic validation.
    """
    # Missing required field 'credential_type'
    payload = {
        "agent_id": "agent_789",
        "tool_call": {"url": "http://example.com/api", "action": "ping"}
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"][0]["loc"] == ["body", "credential_type"]

def test_auth_missing_key():
    """
    Test that requests without an API key are rejected with a 401.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api"},
        "credential_type": "test"
    }
    response = client.post("/proxy/execute", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()

def test_auth_invalid_key():
    """
    Test that requests with an invalid API key are rejected with a 401.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api"},
        "credential_type": "test"
    }
    response = client.post("/proxy/execute", json=payload, headers={"Authorization": "Bearer wrong_key"})
    assert response.status_code == 401
    assert "detail" in response.json()

def test_auth_x_api_key_header():
    """
    Test that the X-API-Key header works as a fallback.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api"},
        "credential_type": "test"
    }
    response = client.post("/proxy/execute", json=payload, headers={"X-API-Key": "test_api_key"})
    # It should pass auth and hit the 422 validation error (since we didn't mock the downstream call)
    # or return 200 if we mocked it. Here we just assert it's not 401.
    assert response.status_code != 401

@pytest.mark.asyncio
async def test_execute_proxy_request_internal_exception():
    """
    Test the internal execute_proxy_request function directly,
    and simulate a 500 error in the endpoint by mocking.
    """
    from unittest.mock import patch
    
    with patch("app.main.execute_proxy_request", side_effect=Exception("Internal Database Error")):
        payload = {
            "agent_id": "agent_err",
            "tool_call": {"url": "http://example.com/api"},
            "credential_type": "test"
        }
        response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
        assert response.status_code == 500
        assert response.json() == {"detail": "An internal server error occurred while processing the proxy request. Please try again later."}


def test_generate_audit_id():
    """
    Test that the generate_audit_id function returns a valid formatted ID.
    """
    from app.audit import generate_audit_id
    audit_id = generate_audit_id()
    assert audit_id.startswith("adt_")
    assert len(audit_id) > 4

def test_log_request(caplog):
    """
    Test that log_request correctly logs the audit details.
    """
    from app.audit import log_request
    import logging
    
    with caplog.at_level(logging.INFO):
        log_request(
            audit_id="adt_test123",
            agent_id="agent_1",
            credential_type="stripe",
            payment_amount=10.0,
            success=True
        )
    
    assert "Audit Log:" in caplog.text
    assert "adt_test123" in caplog.text
    assert "agent_1" in caplog.text
    assert "stripe" in caplog.text
    assert "10.0" in caplog.text

def test_get_supabase_client():
    """
    Test get_supabase_client initialization.
    """
    from app.supabase import get_supabase_client
    from app.config import settings
    import app.supabase
    
    # Test when HAS_SUPABASE is False
    app.supabase.HAS_SUPABASE = False
    assert get_supabase_client() is None
    
    # Test when HAS_SUPABASE is True but no config
    app.supabase.HAS_SUPABASE = True
    settings.SUPABASE_URL = ""
    settings.SUPABASE_KEY = ""
    assert get_supabase_client() is None
    
    # Test when HAS_SUPABASE is True and config is present
    settings.SUPABASE_URL = "http://test.com"
    settings.SUPABASE_KEY = "test_key"
    with patch("app.supabase.create_client") as mock_create:
        mock_create.return_value = "mock_client"
        assert get_supabase_client() == "mock_client"
        
        # Test create_client exception
        mock_create.side_effect = Exception("Create Error")
        assert get_supabase_client() is None
    
    # Reset
    settings.SUPABASE_URL = ""
    settings.SUPABASE_KEY = ""

def test_supabase_real_client_paths():
    """
    Test the Supabase functions when a real client is configured.
    """
    from app.supabase import create_tables, insert_agent, rotate_credential_db, fetch_credential, get_agent_scopes
    from unittest.mock import MagicMock, patch
    
    mock_client = MagicMock()
    # Mock create_tables
    with patch("app.supabase.get_supabase_client", return_value=mock_client):
        # create_tables success
        assert create_tables() is True
        
        # create_tables failure
        mock_client.rpc.side_effect = Exception("DB Error")
        # Wait, create_tables doesn't use rpc anymore, it just logs
        
        # insert_agent success
        mock_client.table().insert().execute.return_value = True
        assert insert_agent("agent_1", "Agent 1") is True
        
        # insert_agent failure
        mock_client.table().insert().execute.side_effect = Exception("Insert Error")
        assert insert_agent("agent_fail", "Fail") is False
        
        # rotate_credential_db success
        mock_client.table().upsert().execute.return_value = True
        assert rotate_credential_db("agent_1", "stripe", {"key": "val"}, "2026-01-01T00:00:00Z") is True
        
        # rotate_credential_db failure
        mock_client.table().upsert().execute.side_effect = Exception("Upsert Error")
        assert rotate_credential_db("agent_fail", "stripe", {"key": "val"}, None) is False
        
        # fetch_credential success
        mock_response = MagicMock()
        mock_response.data = [{"secret_data": {"key": "val"}, "scopes": ["read"]}]
        mock_client.table().select().eq().eq().execute.return_value = mock_response
        assert fetch_credential("agent_1", "stripe") == {"key": "val"}
        
        # fetch_credential no data
        mock_response.data = []
        mock_client.table().select().eq().eq().execute.return_value = mock_response
        assert fetch_credential("agent_2", "stripe") is None
        
        # fetch_credential error
        mock_client.table().select().eq().eq().execute.side_effect = Exception("Select Error")
        assert fetch_credential("agent_fail", "stripe") is None
        
        # get_agent_scopes success
        mock_response.data = [{"credential_type": "stripe", "scopes": ["read"]}]
        mock_client.table().select().eq().execute.return_value = mock_response
        assert get_agent_scopes("agent_3") == {"stripe": ["read"]}
        
        # Test schema file not found
        with patch("os.path.exists", return_value=False):
            assert create_tables() is False
            
        # Test create_tables exception reading file
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Read Error")):
                assert create_tables() is False
                
        # Test get_agent_scopes cache hit
        from app.cache import set_cached_agent_scopes
        set_cached_agent_scopes("agent_cached_scopes", {"stripe": ["read"]})
        assert get_agent_scopes("agent_cached_scopes") == {"stripe": ["read"]}
        
        # get_agent_scopes error
        mock_client.table().select().eq().execute.side_effect = Exception("Select Error")
        # It falls back to simulation
        assert get_agent_scopes("fail") == {}
        
        # Test schema file not found
        with patch("os.path.exists", return_value=False):
            assert create_tables() is False
            
        # Test create_tables exception reading file
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Read Error")):
                assert create_tables() is False
                
        # Test get_agent_scopes cache hit
        from app.cache import set_cached_agent_scopes
        set_cached_agent_scopes("agent_cached_scopes", {"stripe": ["read"]})
        assert get_agent_scopes("agent_cached_scopes") == {"stripe": ["read"]}
        
        # Test fetch_credential return None at end
        # This happens if secret_data is None but it didn't return early.
        mock_client.table().select().eq().eq().execute.side_effect = Exception("Select Error")
        assert fetch_credential("agent_fail", "stripe") is None

def test_supabase_schema_exists_and_valid():
    """
    Verify that the Supabase schema file exists and contains the required
    MCP/A2A-native fields (protocol_version, a2a_capabilities, scopes).
    """
    import os
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "supabase", "schema.sql")
    assert os.path.exists(schema_path), "schema.sql must exist in the supabase/ directory"
    
    with open(schema_path, "r") as f:
        content = f.read()
        
    assert "CREATE TABLE IF NOT EXISTS public.agents" in content
    assert "CREATE TABLE IF NOT EXISTS public.credentials" in content
    assert "protocol_version" in content
    assert "a2a_capabilities" in content
    assert "scopes" in content

def test_create_tables_simulation():
    """
    Test the create_tables helper in simulation mode.
    """
    from app.supabase import create_tables
    # In our test environment, Supabase is not fully configured, so it should simulate
    result = create_tables()
    assert result is True

def test_agent_registration_success():
    """
    Test the /agents/register endpoint with valid payload and auth.
    """
    payload = {
        "agent_id": "agent_new_123",
        "name": "Test Agent",
        "metadata": {"purpose": "testing"}
    }
    response = client.post("/agents/register", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["agent_id"] == "agent_new_123"
    assert data["name"] == "Test Agent"
    assert "created_at" in data

def test_agent_registration_unauthorized():
    """
    Test the /agents/register endpoint without auth.
    """
    payload = {
        "agent_id": "agent_new_123",
        "name": "Test Agent"
    }
    response = client.post("/agents/register", json=payload)
    assert response.status_code == 401

def test_proxy_execute_scope_success():
    """
    Test the /proxy/execute endpoint with valid required scopes.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "read_data", "required_scopes": ["read"]},
        "credential_type": "stripe_live"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200

def test_proxy_execute_scope_denial():
    """
    Test the /proxy/execute endpoint when requested scopes exceed granted scopes.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"url": "http://example.com/api", "action": "delete_data", "required_scopes": ["admin"]},
        "credential_type": "stripe_live"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 403
    assert response.json()["error_code"] == "INSUFFICIENT_SCOPES"
    assert "Insufficient permissions" in response.json()["message"]

def test_get_agent_scopes():
    """
    Test the /agents/{agent_id}/scopes endpoint.
    """
    response = client.get("/agents/agent_123/scopes", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "agent_123"
    assert "scopes" in data
    assert "stripe_live" in data["scopes"]

@patch("app.identity.insert_agent")
def test_agent_registration_db_failure(mock_insert):
    """
    Test the /agents/register endpoint when DB insertion fails.
    """
    mock_insert.return_value = False
    payload = {
        "agent_id": "agent_fail",
        "name": "Fail Agent"
    }
    response = client.post("/agents/register", json=payload, headers=get_auth_headers())
    assert response.status_code == 500
    assert response.json()["error_code"] == "REGISTRATION_FAILED"
    assert "Failed to register agent" in response.json()["message"]

def test_credential_rotation_success():
    """
    Test the /credentials/rotate endpoint with valid payload, auth, and expiry.
    """
    payload = {
        "agent_id": "agent_123",
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_live_new123"},
        "expires_in_days": 30.0
    }
    response = client.post("/credentials/rotate", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["agent_id"] == "agent_123"
    assert data["credential_type"] == "stripe_live"
    assert data["expires_at"] is not None

def test_credential_rotation_no_expiry():
    """
    Test the /credentials/rotate endpoint without an explicit expiry.
    """
    payload = {
        "agent_id": "agent_123",
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_live_new123"}
    }
    response = client.post("/credentials/rotate", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["expires_at"] is None

def test_credential_rotation_unauthorized():
    """
    Test the /credentials/rotate endpoint without auth.
    """
    payload = {
        "agent_id": "agent_123",
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_live_new123"}
    }
    response = client.post("/credentials/rotate", json=payload)
    assert response.status_code == 401

@patch("app.identity.rotate_credential_db")
def test_credential_rotation_db_failure(mock_rotate):
    """
    Test the /credentials/rotate endpoint when DB rotation fails.
    """
    mock_rotate.return_value = False
    payload = {
        "agent_id": "agent_fail",
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_live_new123"}
    }
    response = client.post("/credentials/rotate", json=payload, headers=get_auth_headers())
    assert response.status_code == 500
    assert response.json()["error_code"] == "ROTATION_FAILED"
    assert "Failed to rotate credential" in response.json()["message"]

@patch("app.proxy.check_rate_limit")
def test_proxy_execute_rate_limited(mock_check_rate_limit):
    """
    Test the /proxy/execute endpoint when an agent is rate limited.
    Expects a 429 Too Many Requests response with a Retry-After header.
    """
    mock_check_rate_limit.return_value = (False, 30)
    
    payload = {
        "agent_id": "agent_rate_limited",
        "tool_call": {"url": "http://example.com/api", "action": "ping"},
        "credential_type": "basic_auth"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    
    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    data = response.json()
    assert "Rate limit exceeded" in data["detail"]
    assert "30 seconds" in data["detail"]

def test_check_rate_limit_direct():
    """
    Directly test the check_rate_limit function behavior.
    """
    from app.rate_limit import check_rate_limit, _limiter
    from app.config import settings
    import time
    
    agent_id = "agent_test_limit"
    key = f"rate_limit:{agent_id}"
    
    # Clear state just in case
    with _limiter._lock:
        _limiter._store[key] = []
    
    # Make max requests
    for _ in range(settings.RATE_LIMIT_MAX_REQUESTS):
        allowed, retry = check_rate_limit(agent_id)
        assert allowed is True
        assert retry == 0
        
    # Next request should be rate limited
    allowed, retry = check_rate_limit(agent_id)
    assert allowed is False
    assert retry > 0
    
    # Manually expire the timestamps to test cleanup
    with _limiter._lock:
        _limiter._store[key] = [time.time() - 100] * settings.RATE_LIMIT_MAX_REQUESTS
    allowed, retry = check_rate_limit(agent_id)
    assert allowed is True
    assert retry == 0

def test_metering_direct():
    """
    Directly test the metering functions for thread-safe usage tracking.
    """
    from app.metering import record_usage, get_usage_stats
    
    agent_id = "agent_metering_test"
    
    # Initial stats should be zero
    stats = get_usage_stats(agent_id)
    assert stats["total_calls"] == 0
    assert stats["total_payment_amount"] == 0.0
    
    # Record usage
    record_usage(agent_id, 5.5)
    record_usage(agent_id, 2.0)
    
    # Check updated stats
    stats = get_usage_stats(agent_id)
    assert stats["total_calls"] == 2
    assert stats["total_payment_amount"] == 7.5
    assert stats["last_used"] > 0.0

@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
def test_proxy_execute_metering_integration(mock_request):
    """
    Test that the /proxy/execute endpoint correctly records usage.
    """
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    agent_id = "agent_integration_metering"
    payload = {
        "agent_id": agent_id,
        "tool_call": {"url": "http://example.com/api", "action": "read_data"},
        "credential_type": "read_only_token",
        "payment_amount": 10.0
    }
    
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    
    from app.metering import get_usage_stats
    stats = get_usage_stats(agent_id)
    assert stats["total_calls"] >= 1
    assert stats["total_payment_amount"] >= 10.0

def test_cache_operations():
    """
    Test the in-memory identity caching layer directly.
    """
    from app.cache import (
        get_cached_credential, set_cached_credential, 
        get_cached_agent_scopes, set_cached_agent_scopes, 
        invalidate_agent_cache, _cred_cache, _scopes_cache
    )
    
    agent_id = "agent_cache_test"
    cred_type = "test_cred"
    secret = {"key": "val"}
    scopes = ["read"]
    
    # Test miss
    assert get_cached_credential(agent_id, cred_type) is None
    assert get_cached_agent_scopes(agent_id) is None
    
    # Test set and hit
    set_cached_credential(agent_id, cred_type, secret, scopes)
    set_cached_agent_scopes(agent_id, {cred_type: scopes})
    
    assert get_cached_credential(agent_id, cred_type) == (secret, scopes)
    assert get_cached_agent_scopes(agent_id) == {cred_type: scopes}
    
    # Test invalidation
    invalidate_agent_cache(agent_id)
    assert get_cached_credential(agent_id, cred_type) is None
    assert get_cached_agent_scopes(agent_id) is None
    
    # Test TTL expiry
    set_cached_credential(agent_id, cred_type, secret, scopes, ttl=-1) # Expired immediately
    assert get_cached_credential(agent_id, cred_type) is None
    
    set_cached_agent_scopes(agent_id, {cred_type: scopes}, ttl=-1)
    assert get_cached_agent_scopes(agent_id) is None

def test_config_defaults():
    """
    Test that the centralized configuration loads with expected defaults.
    """
    from app.config import settings
    assert settings.ALLOWED_ORIGINS == ["*"]
    assert settings.SUPABASE_URL == ""
    assert settings.SUPABASE_KEY == ""

def test_health_check():
    """
    Test the /health endpoint returns the correct status and metadata.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

def test_metrics_endpoint():
    """
    Test the /metrics endpoint returns the correct status, uptime, and usage metadata.
    """
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "total_agents_metered" in data
    assert isinstance(data["total_agents_metered"], int)

def test_security_headers():
    """
    Test that the security headers middleware is correctly applying headers to responses.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

def test_cors_headers():
    """
    Test that the CORS middleware is correctly applying the access-control headers.
    """
    response = client.options(
        "/proxy/execute",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert response.status_code == 200
    # FastAPI's CORSMiddleware reflects the Origin header when allow_origins=["*"] and allow_credentials=True
    assert response.headers.get("access-control-allow-origin") == "http://example.com"

def test_proxy_execute_a2a_routing():
    """
    Test that the /proxy/execute endpoint correctly routes A2A calls.
    """
    payload = {
        "agent_id": "agent_123",
        "tool_call": {"target_agent_id": "agent_456", "action": "ping"},
        "credential_type": "stripe_live"
    }
    response = client.post("/proxy/execute", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["success"] is True

@patch("app.supabase.get_agent_scopes")
def test_get_agent_scopes_endpoint_exception(mock_get_scopes):
    mock_get_scopes.side_effect = Exception("Scopes Error")
    response = client.get("/agents/agent_1/scopes", headers=get_auth_headers())
    assert response.status_code == 500

@patch("app.supabase.get_agent_scopes")
def test_get_agent_scopes_endpoint_uae_error(mock_get_scopes):
    from app.errors import AgentNotFoundError
    mock_get_scopes.side_effect = AgentNotFoundError("agent_1")
    response = client.get("/agents/agent_1/scopes", headers=get_auth_headers())
    assert response.status_code == 404

def test_a2a_route_endpoint():
    """
    Test the direct /a2a/route endpoint.
    """
    payload = {
        "source_agent_id": "agent_1",
        "target_agent_id": "agent_2",
        "tool_call": {"action": "do_something"}
    }
    response = client.post("/a2a/route", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "executed successfully" in response.json()["message"]

@patch("app.main.route_tool_call")
def test_a2a_route_endpoint_failure(mock_route):
    """
    Test the direct /a2a/route endpoint when routing fails.
    """
    mock_route.side_effect = Exception("Routing Error")
    payload = {
        "source_agent_id": "agent_1",
        "target_agent_id": "agent_2",
        "tool_call": {"action": "do_something"}
    }
    response = client.post("/a2a/route", json=payload, headers=get_auth_headers())
    assert response.status_code == 500
    assert "internal server error" in response.json()["detail"].lower()

def test_billing_calculation():
    """
    Test the usage-based billing calculation logic directly.
    """
    from app.billing import calculate_usage_invoice
    from app.metering import record_usage
    
    agent_id = "agent_billing_test"
    # Record some usage first
    record_usage(agent_id, 10.0)
    record_usage(agent_id, 5.0)
    
    invoice = calculate_usage_invoice(agent_id)
    assert invoice.invoice_id.startswith("inv_")
    assert invoice.agent_id == agent_id
    assert invoice.total_calls >= 2
    assert invoice.total_payment_volume >= 15.0
    assert invoice.amount_due == invoice.total_calls * invoice.applied_rate
    assert invoice.status == "draft"

def test_billing_invoice_endpoint():
    """
    Test the /billing/invoice/{agent_id} endpoint.
    """
    agent_id = "agent_billing_endpoint"
    
    # Endpoint should return a valid invoice
    response = client.get(f"/billing/invoice/{agent_id}", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == agent_id
    assert "invoice_id" in data
    assert "amount_due" in data
    assert data["status"] == "draft"

@patch("app.main.calculate_usage_invoice")
def test_billing_invoice_endpoint_failure(mock_calc):
    """
    Test the /billing/invoice/{agent_id} endpoint when calculation fails.
    """
    mock_calc.side_effect = Exception("Billing Error")
    response = client.get("/billing/invoice/agent_fail", headers=get_auth_headers())
    assert response.status_code == 500
    assert "internal server error" in response.json()["detail"].lower()

def test_dashboard_stats_endpoint():
    """
    Test the /stats endpoint returns correct aggregated data.
    """
    from app.metering import record_usage
    from app.billing import calculate_usage_invoice
    
    # Ensure some data exists
    record_usage("agent_stats_1", 10.0)
    record_usage("agent_stats_2", 5.0)
    calculate_usage_invoice("agent_stats_1")
    
    response = client.get("/stats", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert "total_agents_registered" in data
    assert data["total_agents_registered"] >= 2
    assert "total_calls" in data
    assert data["total_calls"] >= 2
    assert "total_revenue" in data
    assert data["total_revenue"] >= 15.0
    assert "active_agents" in data
    assert data["active_agents"] >= 2
    assert "recent_activity" in data
    assert len(data["recent_activity"]) >= 2
    assert "recent_invoices" in data
    assert len(data["recent_invoices"]) >= 1

def test_dashboard_stats_unauthorized():
    """
    Test the /stats endpoint requires auth.
    """
    response = client.get("/stats")
    assert response.status_code == 401

@patch("app.main.get_analytics_stats")
def test_dashboard_stats_failure(mock_stats):
    """
    Test the /stats endpoint handles internal errors gracefully.
    """
    mock_stats.side_effect = Exception("Stats Error")
    response = client.get("/stats", headers=get_auth_headers())
    assert response.status_code == 500
    assert "internal server error" in response.json()["detail"].lower()

@pytest.mark.asyncio
@patch("app.routing.get_cached_agent_scopes")
async def test_route_tool_call_cache_hit(mock_get_cache):
    """
    Test route_tool_call when target agent is in cache.
    """
    from app.routing import route_tool_call
    mock_get_cache.return_value = {"stripe": ["read"]}
    
    success = await route_tool_call("source_agent", {"target_agent_id": "agent_in_cache"})
    assert success is True

@patch("app.main.register_agent")
def test_agents_register_exception(mock_reg):
    mock_reg.side_effect = Exception("DB Error")
    payload = {"agent_id": "agent_err", "name": "Err"}
    response = client.post("/agents/register", json=payload, headers=get_auth_headers())
    assert response.status_code == 500

@patch("app.main.rotate_credential")
def test_credentials_rotate_exception(mock_rot):
    mock_rot.side_effect = Exception("DB Error")
    payload = {"agent_id": "agent_err", "credential_type": "stripe", "new_secret_data": {}}
    response = client.post("/credentials/rotate", json=payload, headers=get_auth_headers())
    assert response.status_code == 500

@patch("app.main.route_tool_call")
def test_a2a_route_uae_error(mock_route):
    from app.errors import InvalidA2ARouteError
    mock_route.side_effect = InvalidA2ARouteError("agent_err")
    payload = {"source_agent_id": "a", "target_agent_id": "agent_err", "tool_call": {}}
    response = client.post("/a2a/route", json=payload, headers=get_auth_headers())
    assert response.status_code == 400

@patch("app.main.calculate_usage_invoice")
def test_get_usage_invoice_uae_error(mock_calc):
    from app.errors import AgentNotFoundError
    mock_calc.side_effect = AgentNotFoundError("agent_err")
    response = client.get("/billing/invoice/agent_err", headers=get_auth_headers())
    assert response.status_code == 404

@patch("app.main.process_payment_webhook")
def test_payment_webhook_exceptions(mock_process):
    import json, hmac, hashlib
    from app.config import settings
    from app.errors import PaymentFailedError
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    payload = {"transaction_id": "tx_123", "status": "success", "amount": 10.0, "agent_id": "agent_1"}
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(key=settings.WEBHOOK_SECRET.encode("utf-8"), msg=body, digestmod=hashlib.sha256).hexdigest()
    headers = {"X-Webhook-Signature": signature, "Content-Type": "application/json"}
    
    # UAEError
    mock_process.side_effect = PaymentFailedError()
    response = client.post("/webhooks/payment", content=body, headers=headers)
    assert response.status_code == 402
    
    # HTTPException
    from fastapi import HTTPException
    mock_process.side_effect = HTTPException(status_code=409, detail="Conflict")
    response = client.post("/webhooks/payment", content=body, headers=headers)
    assert response.status_code == 409
    
    # Generic Exception
    mock_process.side_effect = Exception("Generic Error")
    response = client.post("/webhooks/payment", content=body, headers=headers)
    assert response.status_code == 500

@patch("app.main.logger.error")
def test_middleware_unhandled_exception(mock_logger):
    # To trigger the middleware exception block, we need to bypass FastAPI's exception handlers.
    # We can do this by mocking the CORS middleware's __call__ method, which is inside call_next.
    from fastapi.middleware.cors import CORSMiddleware
    with patch.object(CORSMiddleware, "__call__", side_effect=Exception("Middleware Error")):
        with pytest.raises(Exception):
            client.get("/")
    mock_logger.assert_called()

def test_check_scopes_direct():
    """
    Directly test the check_scopes helper.
    """
    from app.identity import check_scopes
    
    assert check_scopes([], ["read"]) is True
    assert check_scopes(["read"], []) is False
    assert check_scopes(["read"], ["read", "write"]) is True
    assert check_scopes(["admin"], ["read", "write"]) is False

def test_analytics_trimming():
    """
    Test that the analytics tracker trims recent activity correctly.
    """
    from app.analytics import AnalyticsTracker, AnalyticsEvent
    import time
    
    tracker = AnalyticsTracker()
    for i in range(60):
        event = AnalyticsEvent(
            event_id=f"evt_{i}",
            agent_id="agent_1",
            event_type="proxy_execute",
            amount=0.0,
            timestamp=time.time()
        )
        tracker.track_event(event)
        
    stats = tracker.get_global_stats()
    # It should only keep the latest 50 events in _store
    assert len(tracker._store["analytics:recent_activity"]) == 50
    # get_global_stats only returns top 10
    assert len(stats["recent_activity"]) == 10

def test_error_classes():
    """
    Test the custom UAEError subclasses.
    """
    from app.errors import PaymentFailedError, InvalidA2ARouteError, AgentNotFoundError
    
    err1 = PaymentFailedError()
    assert err1.error_code == "PAYMENT_FAILED"
    assert err1.status_code == 402
    
    err2 = InvalidA2ARouteError(target_agent_id="agent_1")
    assert err2.error_code == "INVALID_A2A_ROUTE"
    assert err2.status_code == 400
    assert err2.details["target_agent_id"] == "agent_1"
    
    err3 = AgentNotFoundError(agent_id="agent_2")
    assert err3.error_code == "AGENT_NOT_FOUND"
    assert err3.status_code == 404
    assert err3.details["agent_id"] == "agent_2"

@pytest.mark.asyncio
@patch("app.routing.get_cached_agent_scopes")
async def test_route_tool_call_cache_hit(mock_get_cache):
    """
    Test route_tool_call when target agent is in cache.
    """
    from app.routing import route_tool_call
    mock_get_cache.return_value = {"stripe": ["read"]}
    
    success = await route_tool_call("source_agent", {"target_agent_id": "agent_in_cache"})
    assert success is True

# --- DAY 21: FULL INTEGRATION TESTS ---

def test_full_identity_flow_success():
    """
    Integration Test: Full Identity Flow (Success)
    1. Register an agent
    2. Rotate/issue a credential with scopes
    3. Call /proxy/execute with valid scopes -> successful injection + A2A stub routing + metering + audit
    """
    agent_id = "agent_integration_1"
    
    # 1. Register
    reg_payload = {"agent_id": agent_id, "name": "Integration Agent"}
    reg_resp = client.post("/agents/register", json=reg_payload, headers=get_auth_headers())
    assert reg_resp.status_code == 200
    
    # 2. Rotate/Issue Credential with scopes
    rot_payload = {
        "agent_id": agent_id,
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_test_123"},
        "expires_in_days": 30
    }
    rot_resp = client.post("/credentials/rotate", json=rot_payload, headers=get_auth_headers())
    assert rot_resp.status_code == 200
    
    # 3. Call /proxy/execute with valid scopes and A2A target
    proxy_payload = {
        "agent_id": agent_id,
        "tool_call": {
            "target_agent_id": "agent_target_1",
            "action": "transfer",
            "required_scopes": ["read"] # Using 'read' as it's provided by the simulation fallback
        },
        "credential_type": "stripe_live",
        "payment_amount": 1.50
    }
    proxy_resp = client.post("/proxy/execute", json=proxy_payload, headers=get_auth_headers())
    assert proxy_resp.status_code == 200
    data = proxy_resp.json()
    
    assert data["success"] is True
    assert data["injected_credential"] is True
    assert data["x402_settled"] is True
    assert "audit_id" in data
    
    # Verify metering
    from app.metering import get_usage_stats
    stats = get_usage_stats(agent_id)
    assert stats["total_calls"] >= 1
    assert stats["total_payment_amount"] >= 1.50

def test_full_identity_flow_scope_denial():
    """
    Integration Test: Full Identity Flow (Scope Denial)
    Call /proxy/execute with insufficient scopes -> 403 Forbidden
    """
    agent_id = "agent_integration_2"
    
    # Call /proxy/execute with invalid scopes
    proxy_payload = {
        "agent_id": agent_id,
        "tool_call": {
            "target_agent_id": "agent_target_2", 
            "action": "delete", 
            "required_scopes": ["super_admin_only"]
        },
        "credential_type": "stripe_live"
    }
    proxy_resp = client.post("/proxy/execute", json=proxy_payload, headers=get_auth_headers())
    assert proxy_resp.status_code == 403
    assert proxy_resp.json()["error_code"] == "INSUFFICIENT_SCOPES"
    assert "Insufficient permissions" in proxy_resp.json()["message"]

def test_cache_invalidation_on_rotation():
    """
    Integration Test: Cache invalidation after rotation
    1. Fetch scopes (caches them)
    2. Rotate credential (invalidates cache)
    3. Verify cache is empty
    """
    from app.cache import get_cached_agent_scopes
    
    agent_id = "agent_integration_3"
    
    # 1. Fetch scopes to populate cache
    client.get(f"/agents/{agent_id}/scopes", headers=get_auth_headers())
    
    # Verify cache hit is possible (it should be populated)
    cached_scopes = get_cached_agent_scopes(agent_id)
    assert cached_scopes is not None
    
    # 2. Rotate credential
    rot_payload = {
        "agent_id": agent_id,
        "credential_type": "aws",
        "new_secret_data": {"key": "val"}
    }
    client.post("/credentials/rotate", json=rot_payload, headers=get_auth_headers())
    
    # 3. Verify cache is invalidated
    assert get_cached_agent_scopes(agent_id) is None

def test_full_identity_flow_a2a_direct():
    """
    Integration Test: Direct A2A Routing
    Call /a2a/route directly and verify it succeeds.
    """
    payload = {
        "source_agent_id": "agent_integration_4",
        "target_agent_id": "agent_target_4",
        "tool_call": {"action": "ping"}
    }
    response = client.post("/a2a/route", json=payload, headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["success"] is True

# --- DAY 24: WEBHOOK TESTS ---

def test_payment_webhook_success():
    """
    Test the /webhooks/payment endpoint with a valid signature and success status.
    """
    import hmac
    import hashlib
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    
    payload = {
        "transaction_id": "tx_123",
        "status": "success",
        "amount": 10.0,
        "agent_id": "agent_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    signature = hmac.new(
        key=settings.WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"X-Webhook-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "received"}

def test_payment_webhook_invalid_signature():
    """
    Test the /webhooks/payment endpoint with an invalid signature.
    """
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    
    payload = {
        "transaction_id": "tx_123",
        "status": "success",
        "amount": 10.0,
        "agent_id": "agent_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"X-Webhook-Signature": "invalid_signature", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_SIGNATURE"
    assert "Invalid webhook signature" in response.json()["message"]

def test_payment_webhook_missing_signature():
    """
    Test the /webhooks/payment endpoint with a missing signature header.
    """
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    
    payload = {
        "transaction_id": "tx_123",
        "status": "success",
        "amount": 10.0,
        "agent_id": "agent_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_SIGNATURE"
    assert "Invalid webhook signature" in response.json()["message"]

def test_payment_webhook_no_secret_configured():
    """
    Test the /webhooks/payment endpoint when WEBHOOK_SECRET is not configured.
    """
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = ""
    
    payload = {
        "transaction_id": "tx_123",
        "status": "success",
        "amount": 10.0,
        "agent_id": "agent_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"X-Webhook-Signature": "any_signature", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_SIGNATURE"
    assert "Invalid webhook signature" in response.json()["message"]

def test_payment_webhook_failure_status():
    """
    Test the /webhooks/payment endpoint with a valid signature but failed status.
    """
    import hmac
    import hashlib
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    
    payload = {
        "transaction_id": "tx_123",
        "status": "failed",
        "amount": 10.0,
        "agent_id": "agent_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    signature = hmac.new(
        key=settings.WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"X-Webhook-Signature": signature, "Content-Type": "application/json"}
    )
    
    # Still returns 200 OK because the webhook was received and processed (even if payment failed)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}

# --- DAY 28: FULL PAYMENTS + IDENTITY INTEGRATION TESTS ---

def test_full_payments_identity_flow_success():
    """
    Integration Test: Full Payments + Identity Flow (Success)
    1. Register an agent
    2. Rotate/issue a credential with scopes
    3. Call /proxy/execute with valid scopes and payment -> successful injection + A2A stub routing + metering + audit
    """
    agent_id = "agent_pay_int_1"
    
    # 1. Register
    reg_payload = {"agent_id": agent_id, "name": "Payment Integration Agent"}
    reg_resp = client.post("/agents/register", json=reg_payload, headers=get_auth_headers())
    assert reg_resp.status_code == 200
    
    # 2. Rotate/Issue Credential with scopes
    rot_payload = {
        "agent_id": agent_id,
        "credential_type": "stripe_live",
        "new_secret_data": {"api_key": "sk_test_pay123"},
        "expires_in_days": 30
    }
    rot_resp = client.post("/credentials/rotate", json=rot_payload, headers=get_auth_headers())
    assert rot_resp.status_code == 200
    
    # 3. Call /proxy/execute with valid scopes and payment
    proxy_payload = {
        "agent_id": agent_id,
        "tool_call": {
            "target_agent_id": "agent_target_pay",
            "action": "transfer",
            "required_scopes": ["read"] # Using 'read' as it's provided by the simulation fallback
        },
        "credential_type": "stripe_live",
        "payment_amount": 10.50
    }
    proxy_resp = client.post("/proxy/execute", json=proxy_payload, headers=get_auth_headers())
    assert proxy_resp.status_code == 200
    data = proxy_resp.json()
    
    assert data["success"] is True
    assert data["injected_credential"] is True
    assert data["x402_settled"] is True
    assert "transaction_id" in data
    assert "audit_id" in data
    
    # Verify metering
    from app.metering import get_usage_stats
    stats = get_usage_stats(agent_id)
    assert stats["total_calls"] >= 1
    assert stats["total_payment_amount"] >= 10.50

def test_full_payments_identity_flow_scope_denial():
    """
    Integration Test: Full Payments + Identity Flow (Scope Denial)
    Call /proxy/execute with insufficient scopes -> 403 Forbidden with structured error
    """
    agent_id = "agent_pay_int_2"
    
    # Call /proxy/execute with invalid scopes
    proxy_payload = {
        "agent_id": agent_id,
        "tool_call": {
            "target_agent_id": "agent_target_2", 
            "action": "delete", 
            "required_scopes": ["super_admin_only"]
        },
        "credential_type": "stripe_live",
        "payment_amount": 5.00
    }
    proxy_resp = client.post("/proxy/execute", json=proxy_payload, headers=get_auth_headers())
    assert proxy_resp.status_code == 403
    assert proxy_resp.json()["error_code"] == "INSUFFICIENT_SCOPES"
    assert "Insufficient permissions" in proxy_resp.json()["message"]

def test_payment_webhook_integration():
    """
    Integration Test: Payment Webhook
    Simulate a webhook call for a transaction generated in the proxy execute step.
    """
    import hmac
    import hashlib
    import json
    from app.config import settings
    
    settings.WEBHOOK_SECRET = "whsec_test_secret"
    
    payload = {
        "transaction_id": "tx_sim_123456",
        "status": "success",
        "amount": 10.50,
        "agent_id": "agent_pay_int_1"
    }
    body = json.dumps(payload).encode("utf-8")
    
    signature = hmac.new(
        key=settings.WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    response = client.post(
        "/webhooks/payment", 
        content=body, 
        headers={"X-Webhook-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "received"}

def test_billing_after_payment():
    """
    Integration Test: Billing Invoice Generation
    After the proxy execute with payment, call /billing/invoice/{agent_id} and verify the invoice.
    """
    agent_id = "agent_pay_int_1"
    
    # Endpoint should return a valid invoice reflecting the payment volume
    response = client.get(f"/billing/invoice/{agent_id}", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == agent_id
    assert "invoice_id" in data
    assert data["total_payment_volume"] >= 10.50
    assert data["status"] == "draft"

def test_cache_invalidation_and_stats_after_payment():
    """
    Integration Test: Cache Invalidation and Stats Dashboard
    Verify /stats reflects the new agent, calls, and revenue after the payment flow.
    """
    response = client.get("/stats", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_agents_registered"] >= 1
    assert data["total_calls"] >= 1
    assert data["total_revenue"] >= 10.50
    assert data["active_agents"] >= 1
    assert len(data["recent_invoices"]) >= 1

# --- DAY 29: SDK TESTS ---

def test_sdk_client_initialization():
    """
    Test that the SDK client initializes correctly.
    """
    from sdk.uaeos.client import UAEOSClient
    
    client = UAEOSClient(api_key="test_key", base_url="http://test.local")
    assert client.api_key == "test_key"
    assert client.base_url == "http://test.local"
    assert client.headers["Authorization"] == "Bearer test_key"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_register_agent(mock_request):
    """
    Test the SDK register_agent method.
    """
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "agent_id": "sdk_agent"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    client = UAEOSClient(api_key="test_key")
    result = await client.register_agent(agent_id="sdk_agent", name="SDK Agent")
    
    assert result["success"] is True
    assert result["agent_id"] == "sdk_agent"
    
    # Verify httpx was called correctly
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "/agents/register"
    assert kwargs["json"]["agent_id"] == "sdk_agent"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_rotate_credential(mock_request):
    """
    Test the SDK rotate_credential method.
    """
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "expires_at": "2024-01-01T00:00:00Z"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    client = UAEOSClient(api_key="test_key")
    result = await client.rotate_credential(
        agent_id="sdk_agent",
        credential_type="stripe",
        new_secret_data={"key": "val"},
        expires_in_days=30.0
    )
    
    assert result["success"] is True
    assert result["expires_at"] == "2024-01-01T00:00:00Z"
    
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "/credentials/rotate"
    assert kwargs["json"]["agent_id"] == "sdk_agent"
    assert kwargs["json"]["expires_in_days"] == 30.0

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_get_scopes(mock_request):
    """
    Test the SDK get_scopes method.
    """
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "sdk_agent", "scopes": {"stripe": ["read"]}}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    client = UAEOSClient(api_key="test_key")
    result = await client.get_scopes(agent_id="sdk_agent")
    
    assert result["agent_id"] == "sdk_agent"
    assert result["scopes"]["stripe"] == ["read"]
    
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert args[1] == "/agents/sdk_agent/scopes"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_get_invoice(mock_request):
    """
    Test the SDK get_invoice method.
    """
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"invoice_id": "inv_123", "amount_due": 10.0}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    client = UAEOSClient(api_key="test_key")
    result = await client.get_invoice(agent_id="sdk_agent")
    
    assert result["invoice_id"] == "inv_123"
    assert result["amount_due"] == 10.0
    
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert args[1] == "/billing/invoice/sdk_agent"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_execute(mock_request):
    """
    Test the SDK execute method.
    """
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "transaction_id": "tx_123"}
    mock_request.return_value = mock_response
    
    client = UAEOSClient(api_key="test_key")
    result = await client.execute(
        agent_id="sdk_agent",
        tool_call={"action": "ping"},
        credential_type="stripe",
        payment_amount=1.0
    )
    
    assert result["success"] is True
    assert result["transaction_id"] == "tx_123"
    
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "/proxy/execute"
    assert kwargs["json"]["payment_amount"] == 1.0

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_error_handling(mock_request):
    """
    Test the SDK error handling and exception mapping.
    """
    from sdk.uaeos.client import UAEOSClient, RateLimitError, AuthError, InsufficientScopesError, APIError
    from unittest.mock import MagicMock
    
    client = UAEOSClient(api_key="test_key")
    
    # Test 401 Auth Error
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 401
    mock_response.json.return_value = {"error_code": "UNAUTHORIZED", "message": "Invalid key"}
    mock_request.return_value = mock_response
    
    with pytest.raises(AuthError) as exc_info:
        await client.get_stats()
    assert exc_info.value.status_code == 401
    
    # Test 403 Scopes Error
    mock_response.status_code = 403
    mock_response.json.return_value = {"error_code": "INSUFFICIENT_SCOPES", "message": "Denied"}
    with pytest.raises(InsufficientScopesError):
        await client.get_stats()
        
    # Test 429 Rate Limit Error
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "5"}
    mock_response.json.return_value = {"error_code": "RATE_LIMIT", "message": "Too fast"}
    # Test 429 Rate Limit Error with retry
    client.max_retries = 1
    mock_success = MagicMock()
    mock_success.is_success = True
    mock_success.status_code = 200
    mock_success.json.return_value = {"success": True}
    
    mock_request.side_effect = [mock_response, mock_success]
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await client.get_stats()
        mock_sleep.assert_called_once_with(5)
        
    # Reset side_effect for next tests
    mock_request.side_effect = None
    mock_request.return_value = mock_response
    
    # Set max_retries to 0 so it fails immediately instead of sleeping
    client.max_retries = 0
    with pytest.raises(RateLimitError) as exc_info:
        await client.get_stats()
    assert exc_info.value.retry_after == 5
    
    # Test Generic API Error (500)
    mock_response.status_code = 500
    mock_response.json.side_effect = Exception("No JSON")
    mock_response.text = "Internal Server Error"
    mock_response.headers = {"X-Request-ID": "req_123"}
    with pytest.raises(APIError) as exc_info:
        await client.get_stats()
    assert exc_info.value.status_code == 500
    assert exc_info.value.request_id == "req_123"
    
    # Test close methods
    await client.close()
    async with UAEOSClient(api_key="test_key") as c:
        pass

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_sdk_retry_logic(mock_request):
    """
    Test the SDK exponential backoff retry logic.
    """
    from sdk.uaeos.client import UAEOSClient, APIError
    from unittest.mock import MagicMock
    import httpx
    
    client = UAEOSClient(api_key="test_key", max_retries=2)
    
    # Simulate a network error followed by a success
    mock_success = MagicMock()
    mock_success.is_success = True
    mock_success.status_code = 200
    mock_success.json.return_value = {"total_calls": 10}
    
    # First call raises RequestError, second call succeeds
    mock_request.side_effect = [httpx.RequestError("Network down"), mock_success]
    
    # We patch asyncio.sleep so the test doesn't actually wait
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.get_stats()
        
    assert result["total_calls"] == 10
    assert mock_request.call_count == 2
    mock_sleep.assert_called_once_with(1.0)
    
    # Test RequestError exhaustion
    mock_request.side_effect = httpx.RequestError("Network down")
    mock_request.call_count = 0
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(APIError) as exc_info:
            await client.get_stats()
        assert "Network error" in str(exc_info.value)
        assert mock_request.call_count == 3 # Initial + 2 retries
        
    # Test 500 Server Error exhaustion
    mock_500 = MagicMock()
    mock_500.is_success = False
    mock_500.status_code = 500
    mock_500.json.return_value = {"message": "Server Error"}
    mock_request.side_effect = [mock_500, mock_500, mock_500]
    mock_request.call_count = 0
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(APIError) as exc_info:
            await client.get_stats()
        assert exc_info.value.status_code == 500
        assert mock_request.call_count == 3

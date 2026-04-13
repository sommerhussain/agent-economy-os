import pytest
from unittest.mock import patch, MagicMock
from app.cache import get_cached_credential, set_cached_credential, invalidate_agent_cache, get_cached_agent_scopes, set_cached_agent_scopes
from app.metering import record_usage, get_usage_stats, get_total_agents_metered
from app.rate_limit import check_rate_limit
import json

@patch("app.cache._redis_client")
def test_cache_redis(mock_redis):
    mock_redis.get.return_value = json.dumps({"secret_data": {"key": "val"}, "scopes": ["read"]}).encode()
    assert get_cached_credential("agent_1", "stripe") == ({"key": "val"}, ["read"])
    
    mock_redis.get.return_value = None
    assert get_cached_credential("agent_2", "stripe") is None
    
    set_cached_credential("agent_1", "stripe", {"key": "val"}, ["read"])
    mock_redis.setex.assert_called()
    
    invalidate_agent_cache("agent_1")
    mock_redis.delete.assert_called()
    
    mock_redis.get.return_value = json.dumps({"stripe": ["read"]}).encode()
    assert get_cached_agent_scopes("agent_1") == {"stripe": ["read"]}
    
    set_cached_agent_scopes("agent_1", {"stripe": ["read"]})
    mock_redis.setex.assert_called()

@patch("app.metering._redis_client")
def test_metering_redis(mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = None
    record_usage("agent_1", 1.5)
    
    mock_redis.hgetall.return_value = {"total_calls": "5", "total_payment_amount": "10.5", "last_used": "12345.0"}
    stats = get_usage_stats("agent_1")
    assert stats["total_calls"] == 5
    assert stats["total_payment_amount"] == 10.5
    
    mock_redis.keys.return_value = ["metering:agent_1", "metering:agent_2"]
    assert get_total_agents_metered() == 2

@patch("app.rate_limit._redis_client")
def test_rate_limit_redis(mock_redis):
    mock_redis.pipeline.return_value.execute.return_value = [1, 1]
    allowed, retry = check_rate_limit("agent_1")
    assert allowed is True
    
    mock_redis.pipeline.return_value.execute.return_value = [11, 1]
    allowed, retry = check_rate_limit("agent_1")
    assert allowed is False
    assert retry > 0

@patch("app.payments.get_stripe_client")
def test_payments_live_mode(mock_get_stripe):
    from app.payments import execute_payment
    from app.config import settings
    
    settings.STRIPE_MODE = "live"
    mock_stripe = MagicMock()
    mock_get_stripe.return_value = mock_stripe
    mock_stripe.PaymentIntent.create.return_value = {"id": "tx_123", "status": "succeeded"}
    
    settled, tx_id, msg = execute_payment(1.0, "agent_1")
    assert settled is True
    assert tx_id == "tx_123"
    
    settings.STRIPE_MODE = "simulation"

def test_supabase_fetch_credential_no_cover():
    from app.supabase import fetch_credential
    pass

@pytest.mark.asyncio
async def test_sdk_get_vertical_packs():
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import AsyncMock
    
    client = UAEOSClient("test")
    client._request = AsyncMock(return_value={"verticals": []})
    res = await client.get_vertical_packs()
    assert res == {"verticals": []}

@pytest.mark.asyncio
async def test_sdk_execute_payment_action():
    from sdk.uaeos.client import UAEOSClient
    from unittest.mock import AsyncMock
    
    client = UAEOSClient("test")
    client.execute = AsyncMock(return_value={"success": True})
    res = await client.execute_payment("agent_1", 5.0, "agent_2", "test_action")
    assert res == {"success": True}

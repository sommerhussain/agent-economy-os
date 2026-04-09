import pytest
from unittest.mock import patch, MagicMock
from app.payments import execute_payment
from app.config import settings
import stripe

def test_execute_payment_simulation():
    """
    Test the execute_payment function in simulation mode.
    """
    settings.STRIPE_MODE = "simulation"
    
    # Valid amount
    success, tx_id, amount = execute_payment(10.0, "agent_1")
    assert success is True
    assert tx_id.startswith("tx_sim_")
    assert amount == 10.0

    # Invalid amount
    success, tx_id, amount = execute_payment(0.0, "agent_1")
    assert success is False
    assert tx_id is None
    assert amount == 0.0

def test_execute_payment_live_no_key():
    """
    Test live mode when STRIPE_SECRET_KEY is not configured.
    """
    settings.STRIPE_MODE = "live"
    settings.STRIPE_SECRET_KEY = ""
    
    success, tx_id, amount = execute_payment(5.0, "agent_2")
    assert success is False
    assert tx_id is None
    
    settings.STRIPE_MODE = "simulation"

@patch("stripe.PaymentIntent.create")
def test_execute_payment_live_success(mock_create):
    """
    Test live mode with a successful mocked Stripe PaymentIntent.
    """
    settings.STRIPE_MODE = "live"
    settings.STRIPE_SECRET_KEY = "sk_test_123"
    
    mock_intent = MagicMock()
    mock_intent.id = "pi_12345"
    mock_create.return_value = mock_intent
    
    success, tx_id, amount = execute_payment(2.5, "agent_3")
    assert success is True
    assert tx_id == "pi_12345"
    assert amount == 2.5
    mock_create.assert_called_once()
    
    settings.STRIPE_MODE = "simulation"
    settings.STRIPE_SECRET_KEY = ""

@patch("stripe.PaymentIntent.create")
def test_execute_payment_live_error(mock_create):
    """
    Test live mode when Stripe throws an error.
    """
    settings.STRIPE_MODE = "live"
    settings.STRIPE_SECRET_KEY = "sk_test_123"
    
    mock_create.side_effect = stripe.StripeError("Test error")
    
    success, tx_id, amount = execute_payment(2.5, "agent_3")
    assert success is False
    assert tx_id is None
    assert amount == 2.5
    
    settings.STRIPE_MODE = "simulation"
    settings.STRIPE_SECRET_KEY = ""

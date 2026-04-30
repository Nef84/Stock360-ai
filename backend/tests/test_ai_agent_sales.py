"""
Tests for AI Agent sales closure with Stripe integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_agent import AIAgentService, SALE_CLOSURE_KEYWORDS


def test_sale_detection_with_stripe_keyword():
    """Test that the AI agent detects sale closure keywords."""
    agent = AIAgentService()

    # Test with "pedido confirmado" which is in SALE_CLOSURE_KEYWORDS
    ai_response = "✅ Pedido confirmado. Nike Air Zoom por $65.00."
    assert agent._detect_sale(ai_response) is True


def test_stripe_service_property():
    """Test that stripe_service property works."""
    agent = AIAgentService()
    # Should be None when no API key is set
    assert agent.stripe_service is None

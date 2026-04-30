"""
Integration test for WhatsApp sales flow.
Tests the complete cycle: message -> AI response -> sale detection -> stock deduction.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inventory import (
    Product, Customer, Conversation, ConversationStatus,
    Sale, Channel
)
from app.services.ai_agent import ai_agent


@pytest.mark.asyncio
async def test_full_sales_flow():
    """Test complete sales flow with mocked AI responses and DB."""
    # Mock DB session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock product
    product = Product(
        name="Nike Air Zoom",
        category="Calzado",
        price=65.0,
        stock=10,
        ai_priority=9,
        is_active=True,
    )
    
    # Mock customer
    customer = Customer(
        name="WhatsApp Test",
        phone="521234567890",
        channel_id="521234567890",
        channel=Channel.WHATSAPP,
    )
    
    # Mock conversation
    conversation = Conversation(
        customer_id=1,
        channel=Channel.WHATSAPP,
        status=ConversationStatus.OPEN,
        ai_active=True,
    )
    
    # Mock AI response for inquiry
    mock_inquiry = {
        "response_text": "Te recomiendo Nike Air Zoom por $65.00",
        "sale_detected": False,
        "escalation_detected": False,
        "product": None,
        "stripe_link": None,
    }
    
    # Mock AI response for sale
    mock_sale = {
        "response_text": "Pedido confirmado. Nike Air Zoom por $65.00.\n\n💳 Paga aquí: https://pay.stripe.com/test_123",
        "sale_detected": True,
        "escalation_detected": False,
        "product": product,
        "stripe_link": "https://pay.stripe.com/test_123",
    }
    
    # Test inquiry - no sale
    with patch.object(ai_agent, 'generate_response', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_inquiry
        response_data = await ai_agent.generate_response(
            db=mock_db,
            conversation=conversation,
            history=[],
            customer_message="Hola, busco zapatos",
        )
        assert response_data["sale_detected"] is False
    
    # Test sale confirmation
    with patch.object(ai_agent, 'generate_response', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_sale
        response_data = await ai_agent.generate_response(
            db=mock_db,
            conversation=conversation,
            history=[],
            customer_message="si, lo quiero",
        )
        assert response_data["sale_detected"] is True
        assert response_data["product"] is not None
        
        # Mock sale creation
        sale = await ai_agent.create_sale_record(
            db=mock_db,
            conversation=conversation,
            product=response_data["product"],
            quantity=1,
        )
        
        # Verify sale created
        assert sale is not None
        assert sale.closed_by_ai is True
        
        # Verify stock deducted (product.stock was 10, now 9)
        assert product.stock == 9
        
        # Verify Stripe link in response
        assert "https://pay.stripe.com" in response_data["response_text"]

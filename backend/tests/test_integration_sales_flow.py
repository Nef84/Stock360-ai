"""
Integration test for full WhatsApp/Messenger sales flow.
"""
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from app.models.inventory import (
    Product, Customer, Conversation, ConversationStatus,
    Sale, Channel
)
from app.services.ai_agent import ai_agent


@pytest.mark.asyncio
async def test_full_sales_flow(test_db):
    """Test complete sales flow with mocked AI responses."""
    # Create product
    product = Product(
        name="Nike Air Zoom",
        category="Calzado",
        price=65.0,
        stock=10,
        ai_priority=9,
        is_active=True,
    )
    test_db.add(product)
    await test_db.flush()

    # Create customer
    customer = Customer(
        name="WhatsApp Test",
        phone="521234567890",
        channel_id="521234567890",
        channel=Channel.WHATSAPP,
    )
    test_db.add(customer)
    await test_db.flush()

    # Create conversation
    conversation = Conversation(
        customer_id=customer.id,
        channel=Channel.WHATSAPP,
        status=ConversationStatus.OPEN,
        ai_active=True,
    )
    test_db.add(conversation)
    await test_db.flush()

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
        "response_text": "Pedido confirmado. Nike Air Zoom por $65.00.",
        "sale_detected": True,
        "escalation_detected": False,
        "product": product,
        "stripe_link": "https://pay.stripe.com/test_123",
    }

    # Test inquiry
    with patch.object(ai_agent, 'generate_response', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_inquiry
        response_data = await ai_agent.generate_response(
            db=test_db,
            conversation=conversation,
            history=[],
            customer_message="Hola, busco zapatos",
        )
        assert response_data["sale_detected"] is False

    # Test sale
    with patch.object(ai_agent, 'generate_response', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_sale
        response_data = await ai_agent.generate_response(
            db=test_db,
            conversation=conversation,
            history=[],
            customer_message="si, lo quiero",
        )
        assert response_data["sale_detected"] is True

        # Create sale record
        sale = await ai_agent.create_sale_record(
            db=test_db,
            conversation=conversation,
            product=response_data["product"],
            quantity=1,
        )
        await test_db.commit()

        # Verify sale
        result = await test_db.execute(select(Sale).where(Sale.id == sale.id))
        db_sale = result.scalar_one_or_none()
        assert db_sale is not None
        assert db_sale.closed_by_ai is True

        # Verify stock deducted
        result = await test_db.execute(select(Product).where(Product.id == product.id))
        updated_product = result.scalar_one()
        assert updated_product.stock == 9

        # Verify Stripe link
        assert "https://pay.stripe.com" in response_data["response_text"]

import pytest
from unittest.mock import patch, MagicMock
from app.services.stripe_service import StripeService, StripeServiceError


def test_create_payment_link_success():
    with patch("app.services.stripe_service.stripe") as mock_stripe:
        mock_link = MagicMock()
        mock_link.url = "https://pay.stripe.com/test_123"
        mock_stripe.PaymentLink.create.return_value = mock_link

        service = StripeService(api_key="sk_test_123", success_url="https://example.com/success")
        url = service.create_payment_link(
            product_name="Nike Air Zoom",
            amount=6500,
            quantity=1,
            success_url="https://example.com/success",
        )
        assert url == "https://pay.stripe.com/test_123"


def test_create_payment_link_failure():
    with patch("app.services.stripe_service.stripe") as mock_stripe:
        mock_stripe.PaymentLink.create.side_effect = Exception("Stripe error")

        service = StripeService(api_key="sk_test_123", success_url="https://example.com/success")
        with pytest.raises(StripeServiceError):
            service.create_payment_link("Product", 1000, 1, "https://example.com/success")

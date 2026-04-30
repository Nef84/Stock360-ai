"""
Stripe Service — Generate payment links for AI-closed sales.
"""
import logging
import stripe
from typing import Optional

logger = logging.getLogger("stock360.stripe")


class StripeServiceError(Exception):
    """Raised when Stripe API call fails."""
    pass


class StripeService:
    """Generate Stripe Payment Links for closed sales."""

    def __init__(self, api_key: str, success_url: str, cancel_url: Optional[str] = None):
        self._api_key = api_key
        self._success_url = success_url
        self._cancel_url = cancel_url or success_url
        stripe.api_key = api_key

    def create_payment_link(
        self,
        product_name: str,
        amount: int,
        quantity: int,
        success_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Create a Stripe Payment Link.

        Args:
            product_name: Display name for the payment page
            amount: Price in cents (e.g., 6500 for $65.00)
            quantity: Number of units
            success_url: Override default success URL
            metadata: Optional metadata to attach to the payment link

        Returns:
            The payment link URL

        Raises:
            StripeServiceError: If the API call fails
        """
        try:
            final_success_url = success_url or self._success_url

            line_item = {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": product_name,
                    },
                    "unit_amount": amount,
                },
                "quantity": quantity,
            }

            link = stripe.PaymentLink.create(
                line_items=[line_item],
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": final_success_url},
                },
                metadata=metadata or {},
            )
            logger.info(f"Created Stripe payment link for {product_name}: {link.url}")
            return link.url
        except Exception as exc:
            logger.error(f"Failed to create Stripe payment link: {exc}")
            raise StripeServiceError(f"Stripe API error: {exc}") from exc

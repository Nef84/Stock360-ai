"""
Channel Service — Unified message sending for WhatsApp and Messenger.
"""
import logging
from typing import Optional
from httpx import AsyncClient, HTTPStatusError
from app.models.inventory import Channel

logger = logging.getLogger("stock360.channels")

class ChannelServiceError(Exception):
    """Raised when channel message sending fails."""
    pass

class ChannelService:
    """Send messages to WhatsApp and Messenger channels."""
    
    def __init__(
        self,
        whatsapp_token: Optional[str],
        whatsapp_phone_id: Optional[str],
        messenger_token: Optional[str],
        messenger_verify_token: Optional[str],
    ):
        self._whatsapp_token = whatsapp_token
        self._whatsapp_phone_id = whatsapp_phone_id
        self._messenger_token = messenger_token
        self._messenger_verify_token = messenger_verify_token
    
    async def send_message(
        self,
        channel: Channel,
        recipient_id: str,
        text: str,
    ) -> bool:
        """
        Send a message via the specified channel.
        
        Args:
            channel: The channel to send the message through
            recipient_id: Phone number (WhatsApp) or PSID (Messenger)
            text: The message text
        
        Returns:
            True if successful, False otherwise
        """
        if channel == Channel.WHATSAPP:
            return await self._send_whatsapp(recipient_id, text)
        elif channel == Channel.MESSENGER:
            return await self._send_messenger(recipient_id, text)
        else:
            logger.warning(f"Unsupported channel: {channel}")
            return False
    
    async def _send_whatsapp(self, phone: str, text: str) -> bool:
        if not self._whatsapp_token or not self._whatsapp_phone_id:
            logger.error("WhatsApp credentials not configured")
            return False
        
        url = f"https://graph.facebook.com/v18.0/{self._whatsapp_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self._whatsapp_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        
        try:
            async with AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"WhatsApp message sent to {phone}")
                return True
        except Exception as exc:
            logger.error(f"Failed to send WhatsApp message: {exc}")
            return False
    
    async def _send_messenger(self, psid: str, text: str) -> bool:
        if not self._messenger_token:
            logger.error("Messenger token not configured")
            return False
        
        url = "https://graph.facebook.com/v18.0/me/messages"
        headers = {
            "Authorization": f"Bearer {self._messenger_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": psid},
            "message": {"text": text},
        }
        
        try:
            async with AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"Messenger message sent to {psid}")
                return True
        except Exception as exc:
            logger.error(f"Failed to send Messenger message: {exc}")
            return False
    
    def verify_messenger_token(self, token: str) -> bool:
        """Verify Messenger webhook verify token."""
        return token == self._messenger_verify_token
    
    def verify_whatsapp_token(self, token: str) -> bool:
        """Verify WhatsApp webhook verify token."""
        return token == self._whatsapp_verify_token

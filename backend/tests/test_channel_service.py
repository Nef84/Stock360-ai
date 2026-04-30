import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.channel_service import ChannelService, ChannelServiceError
from app.models.inventory import Channel

@pytest.mark.asyncio
async def test_send_whatsapp_message():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.channel_service.AsyncClient", return_value=mock_client):
        service = ChannelService(
            whatsapp_token="test_token",
            whatsapp_phone_id="123456",
            messenger_token=None,
            messenger_verify_token=None,
        )
        result = await service.send_message(
            channel=Channel.WHATSAPP,
            recipient_id="521234567890",
            text="Hola, ¿cómo puedo ayudarte?",
        )
        assert result is True

@pytest.mark.asyncio
async def test_send_messenger_message():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.channel_service.AsyncClient", return_value=mock_client):
        service = ChannelService(
            whatsapp_token=None,
            whatsapp_phone_id=None,
            messenger_token="page_token_123",
            messenger_verify_token="verify_token",
        )
        result = await service.send_message(
            channel=Channel.MESSENGER,
            recipient_id="psid_123",
            text="¡Gracias por tu compra!",
        )
        assert result is True

@pytest.mark.asyncio
async def test_send_message_failure():
    from httpx import HTTPStatusError
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=HTTPStatusError("Bad Request", request=MagicMock(), response=MagicMock(status_code=400)))

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.channel_service.AsyncClient", return_value=mock_client):
        service = ChannelService(
            whatsapp_token="test_token",
            whatsapp_phone_id="123456",
            messenger_token=None,
            messenger_verify_token=None,
        )
        result = await service.send_message(
            channel=Channel.WHATSAPP,
            recipient_id="521234567890",
            text="Test",
        )
        assert result is False

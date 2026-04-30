"""
WhatsApp & Messenger webhook router
"""
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["webhooks"])


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    from app.config import settings
    if hub_mode == "subscribe" and hub_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    body = await request.json()
    return {"status": "ok"}


@router.post("/messenger")
async def messenger_webhook(request: Request):
    body = await request.json()
    return {"status": "ok"}

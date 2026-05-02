"""
WhatsApp & Messenger webhook router
"""
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.inventory import Customer, Conversation, Message, MessageSource, Channel, ConversationStatus
from app.services.ai_agent import ai_agent

router = APIRouter(tags=["webhooks"])


def extract_whatsapp_message(body: dict) -> tuple[str, str]:
    """Extract phone number and message from WhatsApp webhook payload."""
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None, None
        
        msg = messages[0]
        phone = msg.get("from", "")
        text = msg.get("text", {}).get("body", "")
        return phone, text
    except Exception:
        return None, None


async def process_message(db: AsyncSession, phone: str, text: str, channel: Channel) -> str:
    """Find or create customer/conversation and process through AI agent."""
    # Find or create customer
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalar_one_or_none()
    
    if not customer:
        customer = Customer(
            name=f"WhatsApp {phone[-4:]}",
            phone=phone,
            channel=channel
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    
    # Find or create active conversation
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.customer_id == customer.id,
            Conversation.status == ConversationStatus.OPEN
        )
        .order_by(Conversation.created_at.desc())
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            customer_id=customer.id,
            channel=channel,
            ai_active=True
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Save customer message
    customer_msg = Message(
        conversation_id=conversation.id,
        content=text,
        source=MessageSource.CUSTOMER
    )
    db.add(customer_msg)
    await db.flush()
    
    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(30)
    )
    history = list(reversed(result.scalars().all()))
    
    # Call AI agent
    ai_result = await ai_agent.generate_response(db, conversation, history, text)
    
    return ai_result.get("response", "")


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
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        phone, text = extract_whatsapp_message(body)
        
        if not phone or not text:
            return {"status": "ok", "message": "No message to process"}
        
        response_text = await process_message(db, phone, text, Channel.WHATSAPP)
        
        return {
            "status": "ok",
            "response": response_text,
            "messaging_product": "whatsapp",
            "to": phone,
            "text": {"body": response_text}
        }
    except Exception as e:
        print(f"WhatsApp webhook error: {e}")
        return {"status": "error", "detail": str(e)}


@router.get("/messenger")
async def verify_messenger_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    from app.config import settings
    if hub_mode == "subscribe" and hub_token == settings.MESSENGER_VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.post("/messenger")
async def messenger_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        # Extract Messenger message (simplified)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Messenger webhook error: {e}")
        return {"status": "error", "detail": str(e)}
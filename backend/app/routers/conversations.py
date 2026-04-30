from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models.inventory import (
    Conversation, ConversationStatus, Message, MessageSource,
    Customer, Channel
)
from app.schemas import (
    ConversationCreate, ConversationOut, ConversationUpdate,
    MessageCreate, MessageOut, AIChatRequest, AIChatResponse, CustomerCreate, CustomerOut
)
from app.core.deps import require_any, require_supervisor
from app.models.user import User
from app.services.ai_agent import ai_agent

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Customers ─────────────────────────────────────────────────────────────────
@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return CustomerOut.model_validate(customer)


# ── Conversations ─────────────────────────────────────────────────────────────
@router.get("", response_model=List[ConversationOut])
async def list_conversations(
    status: Optional[ConversationStatus] = None,
    channel: Optional[Channel] = None,
    include_hidden: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    q = select(Conversation)
    if status:
        q = q.where(Conversation.status == status)
    if channel:
        q = q.where(Conversation.channel == channel)
    q = q.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
    result = await db.execute(q)
    conversations = result.scalars().all()
    if not include_hidden:
        conversations = [
            conversation for conversation in conversations
            if "hidden" not in (conversation.tags or [])
        ]
    return [ConversationOut.model_validate(c) for c in conversations]


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    conv = Conversation(customer_id=body.customer_id, channel=body.channel)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    # eager load customer
    result = await db.execute(select(Conversation).where(Conversation.id == conv.id))
    return ConversationOut.model_validate(result.scalar_one())


@router.get("/{conv_id}", response_model=ConversationOut)
async def get_conversation(
    conv_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_any)
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return ConversationOut.model_validate(c)


@router.patch("/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: int,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)

    if body.status == ConversationStatus.CLOSED and not c.closed_at:
        c.closed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(c)
    return ConversationOut.model_validate(c)


@router.post("/{conv_id}/hide", response_model=ConversationOut)
async def hide_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    tags = list(conversation.tags or [])
    if "hidden" not in tags:
        tags.append("hidden")
    conversation.tags = tags
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.post("/hide-closed")
async def hide_closed_conversations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    result = await db.execute(select(Conversation).where(Conversation.status == ConversationStatus.CLOSED))
    conversations = result.scalars().all()
    updated = 0
    for conversation in conversations:
        tags = list(conversation.tags or [])
        if "hidden" not in tags:
            tags.append("hidden")
            conversation.tags = tags
            conversation.updated_at = datetime.now(timezone.utc)
            updated += 1
    await db.commit()
    return {"hidden": updated}


# ── Messages ──────────────────────────────────────────────────────────────────
@router.get("/{conv_id}/messages", response_model=List[MessageOut])
async def get_messages(
    conv_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id)
        .order_by(Message.created_at).offset(skip).limit(limit)
    )
    return [MessageOut.model_validate(m) for m in result.scalars().all()]


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    conv_id: int,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """Send a manual message (human agent)."""
    msg = Message(
        conversation_id=conv_id,
        content=body.content,
        source=MessageSource.AGENT,
        sender_id=current_user.id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return MessageOut.model_validate(msg)


# ── AI Chat ───────────────────────────────────────────────────────────────────
@router.post("/ai/chat", response_model=AIChatResponse)
async def ai_chat(
    body: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any),
):
    """
    Submit a customer message → Aria (AI agent) responds.
    Handles sale detection, stock deduction, and escalation.
    """
    result = await db.execute(select(Conversation).where(Conversation.id == body.conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not conv.ai_active:
        raise HTTPException(status_code=400, detail="IA desactivada en esta conversación")

    # Save customer message
    customer_msg = Message(
        conversation_id=conv.id,
        content=body.customer_message,
        source=MessageSource.CUSTOMER,
    )
    db.add(customer_msg)
    await db.flush()

    # Load history
    hist_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id)
        .order_by(desc(Message.created_at)).limit(30)
    )
    history = list(reversed(hist_result.scalars().all()))

    # Call AI
    ai_result = await ai_agent.generate_response(db, conv, history, body.customer_message)

    # Save AI response
    ai_msg = Message(
        conversation_id=conv.id,
        content=ai_result["response_text"],
        source=MessageSource.AI,
    )
    db.add(ai_msg)
    await db.flush()

    sale_id = None
    if ai_result["sale_detected"] and ai_result["product"]:
        sale = await ai_agent.create_sale_record(db, conv, ai_result["product"])
        sale_id = sale.id
        conv.status = ConversationStatus.CLOSED

    if ai_result["escalation_detected"]:
        conv.ai_active = False
        conv.status = ConversationStatus.ESCALATED

    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return AIChatResponse(
        message=MessageOut.model_validate(customer_msg),
        ai_response=MessageOut.model_validate(ai_msg),
        sale_detected=ai_result["sale_detected"],
        sale_id=sale_id,
        escalated=ai_result["escalation_detected"],
    )

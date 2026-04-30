import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ─── Product ──────────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id:          Mapped[int]   = mapped_column(primary_key=True, index=True)
    name:        Mapped[str]   = mapped_column(String(200), nullable=False, index=True)
    category:    Mapped[str]   = mapped_column(String(100), nullable=False)
    description: Mapped[str]   = mapped_column(Text, nullable=True)
    price:       Mapped[float] = mapped_column(Float, nullable=False)
    cost:        Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stock:       Mapped[int]   = mapped_column(Integer, default=0)
    reserved:    Mapped[int]   = mapped_column(Integer, default=0)   # reserved by AI
    margin_pct:  Mapped[float] = mapped_column(Float, default=0.0)
    sku:         Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    image_url:   Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active:   Mapped[bool]  = mapped_column(Boolean, default=True)
    ai_priority: Mapped[int]   = mapped_column(Integer, default=5)    # 1-10 AI push score
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def available_stock(self) -> int:
        return max(0, self.stock - self.reserved)


# ─── Customer ─────────────────────────────────────────────────────────────────
class Channel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    WEB      = "web"
    MANUAL   = "manual"


class Customer(Base):
    __tablename__ = "customers"

    id:           Mapped[int]     = mapped_column(primary_key=True, index=True)
    name:         Mapped[str]     = mapped_column(String(200), nullable=False)
    phone:        Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email:        Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    channel_id:   Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)   # external ID (WhatsApp number, etc.)
    channel:      Mapped[Channel] = mapped_column(SAEnum(Channel), default=Channel.WEB)
    metadata_:    Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    is_blocked:   Mapped[bool]    = mapped_column(Boolean, default=False)
    total_spent:  Mapped[float]   = mapped_column(Float, default=0.0)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ─── Conversation ─────────────────────────────────────────────────────────────
class ConversationStatus(str, enum.Enum):
    OPEN       = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED  = "escalated"
    CLOSED     = "closed"


class Conversation(Base):
    __tablename__ = "conversations"

    id:          Mapped[int]                = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int]                = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    channel:     Mapped[Channel]            = mapped_column(SAEnum(Channel), nullable=False)
    status:      Mapped[ConversationStatus] = mapped_column(SAEnum(ConversationStatus), default=ConversationStatus.OPEN, index=True)
    ai_active:   Mapped[bool]               = mapped_column(Boolean, default=True)
    assigned_to: Mapped[int | None]         = mapped_column(ForeignKey("users.id"), nullable=True)
    escalation_reason: Mapped[str | None]   = mapped_column(Text, nullable=True)
    tags:        Mapped[list | None]        = mapped_column(JSON, nullable=True)
    created_at:  Mapped[datetime]           = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:  Mapped[datetime]           = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at:   Mapped[datetime | None]    = mapped_column(DateTime(timezone=True), nullable=True)

    customer:    Mapped["Customer"]         = relationship("Customer", foreign_keys=[customer_id], lazy="joined")
    messages:    Mapped[list["Message"]]    = relationship("Message", back_populates="conversation", order_by="Message.created_at")


# ─── Message ──────────────────────────────────────────────────────────────────
class MessageSource(str, enum.Enum):
    CUSTOMER = "customer"
    AI       = "ai"
    AGENT    = "agent"
    SYSTEM   = "system"


class Message(Base):
    __tablename__ = "messages"

    id:              Mapped[int]           = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int]           = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    content:         Mapped[str]           = mapped_column(Text, nullable=False)
    source:          Mapped[MessageSource] = mapped_column(SAEnum(MessageSource), nullable=False)
    sender_id:       Mapped[int | None]    = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_read:         Mapped[bool]          = mapped_column(Boolean, default=False)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


# ─── Sale ─────────────────────────────────────────────────────────────────────
class SaleStatus(str, enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    SHIPPED   = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Sale(Base):
    __tablename__ = "sales"

    id:              Mapped[int]        = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    product_id:      Mapped[int]        = mapped_column(ForeignKey("products.id"), nullable=False)
    customer_id:     Mapped[int]        = mapped_column(ForeignKey("customers.id"), nullable=False)
    quantity:        Mapped[int]        = mapped_column(Integer, default=1)
    unit_price:      Mapped[float]      = mapped_column(Float, nullable=False)
    total:           Mapped[float]      = mapped_column(Float, nullable=False)
    status:          Mapped[SaleStatus] = mapped_column(SAEnum(SaleStatus), default=SaleStatus.PENDING)
    closed_by_ai:    Mapped[bool]       = mapped_column(Boolean, default=False)
    notes:           Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product:  Mapped["Product"]      = relationship("Product", foreign_keys=[product_id], lazy="joined")
    customer: Mapped["Customer"]     = relationship("Customer", foreign_keys=[customer_id], lazy="joined")

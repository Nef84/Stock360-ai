"""
Pydantic schemas for request validation and response serialization.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole
from app.models.inventory import Channel, ConversationStatus, MessageSource, SaleStatus
import re


# ─── Auth ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str  = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.AGENT

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


# ─── Product ──────────────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name:        str   = Field(..., min_length=2, max_length=200)
    category:    str   = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price:       float = Field(..., gt=0)
    cost:        float = Field(0.0, ge=0)
    stock:       int   = Field(0, ge=0)
    margin_pct:  float = Field(0.0, ge=0, le=100)
    sku:         Optional[str] = None
    image_url:   Optional[str] = None
    ai_priority: int   = Field(5, ge=1, le=10)


class ProductOut(BaseModel):
    id:              int
    name:            str
    category:        str
    description:     Optional[str]
    price:           float
    cost:            float
    stock:           int
    reserved:        int
    available_stock: int
    margin_pct:      float
    sku:             Optional[str]
    image_url:       Optional[str]
    is_active:       bool
    ai_priority:     int
    updated_at:      datetime

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    name:        Optional[str]   = None
    category:    Optional[str]   = None
    description: Optional[str]   = None
    price:       Optional[float] = Field(None, gt=0)
    cost:        Optional[float] = Field(None, ge=0)
    stock:       Optional[int]   = Field(None, ge=0)
    margin_pct:  Optional[float] = Field(None, ge=0, le=100)
    is_active:   Optional[bool]  = None
    ai_priority: Optional[int]   = Field(None, ge=1, le=10)


class StockAdjust(BaseModel):
    delta: int   = Field(..., description="Positive to add, negative to remove")
    reason: str  = Field(..., min_length=3)


class ProductImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: List[str] = []


# ─── Customer ─────────────────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name:       str     = Field(..., min_length=2)
    phone:      Optional[str] = None
    email:      Optional[EmailStr] = None
    channel_id: Optional[str] = None
    channel:    Channel = Channel.WEB


class CustomerOut(BaseModel):
    id:          int
    name:        str
    phone:       Optional[str]
    email:       Optional[str]
    channel:     Channel
    total_spent: float
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─── Conversation ─────────────────────────────────────────────────────────────
class ConversationCreate(BaseModel):
    customer_id: int
    channel:     Channel


class ConversationOut(BaseModel):
    id:          int
    customer:    CustomerOut
    channel:     Channel
    status:      ConversationStatus
    ai_active:   bool
    assigned_to: Optional[int]
    tags:        Optional[List[str]]
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status:           Optional[ConversationStatus] = None
    ai_active:        Optional[bool]               = None
    assigned_to:      Optional[int]                = None
    escalation_reason:Optional[str]                = None
    tags:             Optional[List[str]]           = None


# ─── Message ──────────────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4096)
    source:  MessageSource = MessageSource.CUSTOMER


class MessageOut(BaseModel):
    id:              int
    conversation_id: int
    content:         str
    source:          MessageSource
    sender_id:       Optional[int]
    created_at:      datetime
    is_read:         bool

    model_config = {"from_attributes": True}


class AIChatRequest(BaseModel):
    conversation_id: int
    customer_message: str = Field(..., min_length=1, max_length=2048)


class AIChatResponse(BaseModel):
    message:        MessageOut
    ai_response:    MessageOut
    sale_detected:  bool = False
    sale_id:        Optional[int] = None
    escalated:      bool = False


# ─── Sale ─────────────────────────────────────────────────────────────────────
class SaleOut(BaseModel):
    id:              int
    product:         ProductOut
    customer:        CustomerOut
    quantity:        int
    unit_price:      float
    total:           float
    status:          SaleStatus
    closed_by_ai:    bool
    created_at:      datetime

    model_config = {"from_attributes": True}


# ─── Analytics ───────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    ai_sales_today:       float
    total_sales_today:    float
    clients_served_ai:    int
    conversion_rate:      float
    avg_response_ms:      float
    open_conversations:   int
    escalated_today:      int


class SalesByDay(BaseModel):
    day:   str
    ai:    float
    human: float


class TopProduct(BaseModel):
    product_id:   int
    product_name: str
    units_sold:   int
    revenue:      float
    pct:          float

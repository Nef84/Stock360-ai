"""
Stock360 AI — FastAPI Application Entry Point
Production-ready with security middleware, rate limiting, CORS, and seeding.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.inventory import Product, Customer, Conversation, Message, Sale   # register all models
from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.conversations import router as conv_router
from app.routers.analytics import router as analytics_router, sales_router
from app.routers.webhooks import router as webhooks_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("stock360")

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ready")

    # Seed admin user + sample inventory
    await seed_initial_data()
    logger.info("✅ Seed data OK")

    yield

    # Cleanup
    await engine.dispose()
    logger.info("👋 Engine disposed")


async def seed_initial_data():
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        # Admin user
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.ADMIN_EMAIL,
                full_name="Administrador",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            logger.info(f"🔐 Admin created: {settings.ADMIN_EMAIL}")

        # Sample products
        prod_count = await db.execute(select(Product).limit(1))
        if not prod_count.scalar_one_or_none():
            products = [
                Product(name="Nike Air Zoom",     category="Calzado",    price=65,  cost=38, stock=12, margin_pct=41, ai_priority=9,  description="Alta amortiguación para running"),
                Product(name="Adidas Run Pro",    category="Calzado",    price=58,  cost=35, stock=8,  margin_pct=40, ai_priority=8,  description="Ligeros y cómodos para correr"),
                Product(name="Puma Speed X",      category="Calzado",    price=72,  cost=42, stock=5,  margin_pct=42, ai_priority=7,  description="Máxima velocidad y agarre"),
                Product(name="Medias Pro Run",    category="Accesorios", price=12,  cost=4,  stock=45, margin_pct=67, ai_priority=10, description="Medias deportivas antihumedad — ¡mayor margen!"),
                Product(name="Camiseta Dry-Fit",  category="Ropa",       price=28,  cost=12, stock=20, margin_pct=57, ai_priority=8,  description="Tejido transpirable para deporte"),
                Product(name="Short Sport Pro",   category="Ropa",       price=22,  cost=9,  stock=15, margin_pct=59, ai_priority=7,  description="Cómodo y ligero para ejercicio"),
                Product(name="Mochila Trail 25L", category="Accesorios", price=45,  cost=22, stock=7,  margin_pct=51, ai_priority=6,  description="Mochila para senderismo y gym"),
                Product(name="Botella Hidro 750", category="Accesorios", price=18,  cost=7,  stock=30, margin_pct=61, ai_priority=9,  description="Botella térmica deportiva"),
            ]
            for p in products:
                db.add(p)
            logger.info("📦 Sample products seeded")

        await db.commit()


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="🤖 Stock360 AI — Plataforma de ventas automáticas con IA",
    docs_url="/api/docs" if settings.DEBUG else None,     # hide docs in prod
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]         = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS — only allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,      prefix="/api/v1")
app.include_router(products_router,  prefix="/api/v1")
app.include_router(conv_router,      prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(sales_router,     prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1/webhooks")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )

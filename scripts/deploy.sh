#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   Stock360 AI — Script de despliegue a producción                      ║
# ║   Uso: bash scripts/deploy.sh                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Prerequisites ─────────────────────────────────────────────────────────────
command -v docker        >/dev/null 2>&1 || error "Docker no instalado"
command -v docker-compose >/dev/null 2>&1 || error "Docker Compose no instalado"

# ── .env check ───────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    error ".env no encontrado. Copia .env.example → .env y completa los valores."
fi

source .env

[ -z "${ANTHROPIC_API_KEY:-}" ]  && error "ANTHROPIC_API_KEY no configurado en .env"
[ -z "${POSTGRES_PASSWORD:-}" ]  && error "POSTGRES_PASSWORD no configurado en .env"
[ -z "${SECRET_KEY:-}" ]         && error "SECRET_KEY no configurado en .env"
[ -z "${REDIS_PASSWORD:-}" ]     && error "REDIS_PASSWORD no configurado en .env"
[ -z "${ADMIN_PASSWORD:-}" ]     && error "ADMIN_PASSWORD no configurado en .env"

[ "${POSTGRES_PASSWORD}" = "CAMBIA_ESTA_CLAVE_AHORA" ] && \
    error "Cambia POSTGRES_PASSWORD del valor por defecto antes de desplegar"
[ "${SECRET_KEY}" = "GENERA_UN_SECRET_KEY_LARGO_Y_ALEATORIO" ] && \
    error "Genera un SECRET_KEY real antes de desplegar"

info "✅ Variables de entorno validadas"

# ── Build & Deploy ────────────────────────────────────────────────────────────
info "🐳 Construyendo imágenes Docker..."
docker compose build --no-cache

info "🚀 Iniciando servicios..."
docker compose up -d

info "⏳ Esperando que los servicios estén listos..."
sleep 8

# Health check
for i in {1..10}; do
    if curl -sf http://localhost/api/health > /dev/null 2>&1; then
        info "✅ Backend saludable"
        break
    fi
    warn "Intento $i/10 — esperando backend..."
    sleep 5
done

info ""
info "╔══════════════════════════════════════════════════╗"
info "║   🚀 Stock360 AI desplegado exitosamente!       ║"
info "╠══════════════════════════════════════════════════╣"
info "║   🌐 App:     http://localhost                  ║"
info "║   📊 API:     http://localhost/api/health       ║"
info "║   🔑 Login:   ${ADMIN_EMAIL:-admin@stock360.ai}"
info "╚══════════════════════════════════════════════════╝"
info ""
info "📋 Comandos útiles:"
info "   Logs backend:  docker compose logs -f backend"
info "   Logs nginx:    docker compose logs -f nginx"
info "   Parar todo:    docker compose down"
info "   Reiniciar:     docker compose restart backend"

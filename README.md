# ⚡ Stock360 AI — Plataforma de Ventas Automáticas con IA

> **Tu vendedor digital que responde, recomienda y cierra ventas 24/7**
> — sin intervención humana.

---

## 🏗️ Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Nginx      │────▶│  React SPA   │     │  Anthropic API  │
│ Reverse Proxy│     │  (Vite/TS)   │     │  (claude-sonnet)│
└──────┬──────┘     └──────────────┘     └────────┬────────┘
       │                                           │
       ▼                                           │
┌─────────────┐     ┌──────────────┐              │
│  FastAPI     │────▶│  PostgreSQL  │◀─────────────┘
│  Backend     │     │  (asyncpg)   │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐
│   Redis      │
│  (rate limit)│
└─────────────┘
```

### Stack completo
| Capa       | Tecnología                              |
|------------|-----------------------------------------|
| Frontend   | React 18 + TypeScript + Vite + Zustand  |
| Backend    | Python 3.12 + FastAPI + asyncpg         |
| IA         | Anthropic Claude Sonnet (via API)       |
| Base datos | PostgreSQL 16                           |
| Cache      | Redis 7                                 |
| Proxy      | Nginx 1.27                              |
| Deploy     | Docker Compose                          |

---

## 🗂️ Estructura del proyecto

```
stock360-ai/
├── backend/
│   ├── app/
│   │   ├── config.py          ← Configuración (pydantic-settings)
│   │   ├── database.py        ← Engine async SQLAlchemy
│   │   ├── main.py            ← FastAPI app + middleware + seeder
│   │   ├── core/
│   │   │   ├── security.py    ← JWT, bcrypt
│   │   │   └── deps.py        ← Guards de autenticación y roles
│   │   ├── models/
│   │   │   ├── user.py        ← Usuario (admin/supervisor/agent)
│   │   │   └── inventory.py   ← Product, Customer, Conversation, Message, Sale
│   │   ├── schemas/           ← Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── auth.py        ← Login, refresh, crear usuario
│   │   │   ├── products.py    ← CRUD productos + ajuste de stock
│   │   │   ├── conversations.py ← Chats + endpoint AI /ai/chat
│   │   │   └── analytics.py   ← Dashboard, ventas por día, top productos
│   │   └── services/
│   │       └── ai_agent.py    ← Aria: lógica del agente IA
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.ts      ← Axios + auto-refresh JWT
│   │   ├── store/auth.ts      ← Zustand auth store
│   │   ├── types/index.ts     ← Todos los tipos TypeScript
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── InboxPage.tsx     ← Panel de chats con IA real
│   │   │   ├── InventoryPage.tsx
│   │   │   ├── AnalyticsPage.tsx
│   │   │   └── SalesPage.tsx
│   │   └── components/layout/
│   │       └── Layout.tsx     ← Sidebar + navegación
│   ├── nginx.conf
│   └── Dockerfile
├── nginx/
│   └── default.conf           ← Reverse proxy + rate limiting
├── scripts/
│   ├── deploy.sh              ← Script de despliegue automatizado
│   └── generate-secrets.py   ← Generador de credenciales seguras
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## 🚀 Puesta en marcha — Paso a paso

### Prerrequisitos
- Docker ≥ 24 y Docker Compose v2
- Git
- Una clave de API de Anthropic (https://console.anthropic.com)

---

### PASO 1 — Clonar / descomprimir

```bash
# Si lo clonaste de Git:
git clone https://github.com/tuusuario/stock360-ai.git
cd stock360-ai

# Si lo descomprimiste:
cd stock360-ai
```

---

### PASO 2 — Generar credenciales seguras

```bash
python scripts/generate-secrets.py
```

Copia los valores que aparecen (los necesitarás en el siguiente paso).

---

### PASO 3 — Configurar variables de entorno

```bash
cp .env.example .env
nano .env   # o usa tu editor favorito
```

**Valores obligatorios a completar:**

| Variable            | Descripción                              |
|---------------------|------------------------------------------|
| `ANTHROPIC_API_KEY` | Tu clave de Anthropic (sk-ant-...)       |
| `SECRET_KEY`        | Cadena aleatoria larga (del script)      |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos           |
| `REDIS_PASSWORD`    | Contraseña de Redis                      |
| `ADMIN_EMAIL`       | Email del administrador inicial          |
| `ADMIN_PASSWORD`    | Contraseña del admin (mín. 8 chars)      |
| `ALLOWED_ORIGINS`   | Tu dominio (ej: https://tudominio.com)   |

---

### PASO 4 — Desplegar

```bash
bash scripts/deploy.sh
```

O manualmente:

```bash
docker compose build --no-cache
docker compose up -d
```

---

### PASO 5 — Verificar

```bash
# Health check
curl http://localhost/api/health

# Ver logs del backend
docker compose logs -f backend

# Ver todos los servicios
docker compose ps
```

Abre el navegador en **http://localhost** e inicia sesión con las credenciales de admin.

---

## 🔐 Seguridad — Lo que está implementado

| Categoría          | Implementación                                           |
|--------------------|----------------------------------------------------------|
| Autenticación      | JWT con access token (30 min) + refresh token (7 días)  |
| Contraseñas        | bcrypt con salt automático                               |
| Autorización       | RBAC: admin / supervisor / agent                         |
| Rate limiting      | 60 req/min global, 10 req/min en login (Nginx + SlowAPI)|
| CORS               | Solo dominios en `ALLOWED_ORIGINS`                       |
| Headers HTTP       | X-Frame-Options, X-Content-Type, XSS-Protection, etc.   |
| Secrets            | Solo por variables de entorno (nunca en código)          |
| Base de datos      | No expuesta fuera de la red Docker                       |
| Backend            | No expuesto directamente (solo vía Nginx)                |
| Input validation   | Pydantic v2 en todos los endpoints                       |

---

## 🤖 Cómo funciona Aria (el agente IA)

1. El cliente envía un mensaje (vía chat del panel)
2. El frontend llama a `POST /api/v1/conversations/ai/chat`
3. El backend carga el historial de la conversación (últimos 20 mensajes)
4. Carga todos los productos activos con stock disponible
5. Construye el system prompt inyectando el inventario real
6. Llama a la API de Anthropic (claude-sonnet)
7. Analiza la respuesta:
   - ¿Detecta cierre de venta? → crea registro de venta + descuenta stock
   - ¿Detecta escalación? → desactiva IA, marca conversación como "escalated"
8. Guarda el mensaje del cliente y la respuesta de Aria en la BD
9. Retorna la respuesta al frontend en tiempo real

---

## 🌐 Integración WhatsApp / Messenger (producción real)

Para conectar WhatsApp Business API real:

1. Crea una app en https://developers.facebook.com/
2. Activa "WhatsApp Business API" y obtén el Phone Number ID
3. Configura el webhook apuntando a: `https://tudominio.com/api/v1/webhooks/whatsapp`
4. Completa `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_ID` en `.env`

> El endpoint de webhook está preparado en el router para recibirlo.
> Solo necesitas descomentar y completar la lógica en `routers/conversations.py`.

---

## 📡 Endpoints principales de la API

| Método | Ruta                                | Descripción                  | Auth      |
|--------|-------------------------------------|------------------------------|-----------|
| POST   | `/api/v1/auth/login`                | Login → tokens JWT           | ❌         |
| POST   | `/api/v1/auth/refresh`              | Renovar access token         | ❌         |
| POST   | `/api/v1/auth/users`                | Crear usuario                | Admin     |
| GET    | `/api/v1/products`                  | Listar productos              | ✅         |
| POST   | `/api/v1/products`                  | Crear producto                | Supervisor|
| PATCH  | `/api/v1/products/{id}`             | Actualizar producto           | Supervisor|
| POST   | `/api/v1/products/{id}/stock`       | Ajustar stock                 | Supervisor|
| GET    | `/api/v1/conversations`             | Listar conversaciones         | ✅         |
| POST   | `/api/v1/conversations/ai/chat`     | 🤖 Chat con Aria (IA real)   | ✅         |
| PATCH  | `/api/v1/conversations/{id}`        | Actualizar estado/escalación  | ✅         |
| GET    | `/api/v1/analytics/dashboard`       | KPIs del dashboard            | ✅         |
| GET    | `/api/v1/analytics/sales-by-day`    | Ventas por día (IA vs humano) | ✅         |
| GET    | `/api/v1/analytics/top-products`    | Top productos más vendidos    | ✅         |
| GET    | `/api/v1/sales`                     | Historial de ventas           | ✅         |
| GET    | `/api/health`                       | Health check                  | ❌         |

> En modo `DEBUG=true`, la documentación Swagger está en `/api/docs`

---

## ⚙️ Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs -f backend
docker compose logs -f nginx

# Reiniciar solo el backend
docker compose restart backend

# Acceder a la base de datos
docker compose exec db psql -U stock360 -d stock360

# Ejecutar en modo desarrollo (sin Docker)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev

# Rebuild de una imagen específica
docker compose build backend --no-cache
docker compose up -d backend

# Backup de la base de datos
docker compose exec db pg_dump -U stock360 stock360 > backup_$(date +%Y%m%d).sql

# Parar todo
docker compose down

# Parar y borrar volúmenes (¡CUIDADO: borra datos!)
docker compose down -v
```

---

## 🔄 Actualizar en producción

```bash
git pull origin main
docker compose build --no-cache
docker compose up -d
docker compose logs -f backend  # verificar que arrancó bien
```

---

## 🛠️ Próximas mejoras sugeridas

- [ ] Webhook real de WhatsApp Business (Meta Cloud API)
- [ ] Webhook de Facebook Messenger
- [ ] Seguimiento automático 2h después de conversación sin cierre
- [ ] SSL automático con Let's Encrypt + Certbot
- [ ] Notificaciones push en tiempo real (WebSocket)
- [ ] Panel de usuarios y roles
- [ ] Exportar reportes a Excel/PDF
- [ ] Machine learning: aprendizaje de qué respuestas convierten más

---

## 🆘 Troubleshooting

| Problema                         | Solución                                                    |
|----------------------------------|-------------------------------------------------------------|
| Backend no arranca               | `docker compose logs backend` — verificar variables de env  |
| Error 401 al hacer login         | Verificar `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env`        |
| IA no responde                   | Verificar `ANTHROPIC_API_KEY` válida y con créditos         |
| Error de CORS                    | Agregar tu dominio a `ALLOWED_ORIGINS` en `.env`            |
| Puerto 80 ocupado                | `sudo lsof -i :80` y detener el proceso conflictivo         |
| DB no conecta                    | `docker compose logs db` — esperar a que esté healthy       |

---

## 📄 Licencia

MIT — Desarrollado por DevNef Corp para Stock360 AI.

# Stock360 AI - WhatsApp & Messenger Sales Agent Design

## Overview

Extend Stock360 AI to connect the Aria sales agent to WhatsApp Business and Facebook Messenger, enabling automatic sales closure with payment links via Stripe. Uses Ollama (local LLM) as the AI provider.

**Objective**: When customers inquire about products via WhatsApp or Messenger, Aria handles the entire conversation, offers complementary products, closes the sale, generates a Stripe payment link, and deducts inventory stock.

---

## Architecture

**Approach A**: Extend the existing system (recommended and approved).

```
WhatsApp/Messenger → Webhooks → Backend → Aria (Ollama) → Response + Sale + Stripe Link
```

### Flow
1. **Incoming Webhook** → Validate signature/token, extract message and customer_id
2. **Find/Create Customer** (by phone_id or PSID)
3. **Find/Create Conversation** (if none open)
4. **Call Aria (Ollama)** with history and products
5. **Aria responds** → If sale detected: create Sale, deduct stock, generate Stripe link
6. **Send response** via the corresponding channel (WhatsApp API / Messenger API)

---

## Webhooks & Channels

### WhatsApp Business (Meta Cloud API)
- **GET** `/api/v1/webhooks/whatsapp` → Verify `hub.verify_token` from `.env`
- **POST** `/api/v1/webhooks/whatsapp` → Parse `from` (phone number) and message text
- **Send responses** via Meta API using `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_ID`

### Facebook Messenger
- **GET** `/api/v1/webhooks/messenger` → Verify token
- **POST** `/api/v1/webhooks/messenger` → Parse `sender.id` (PSID) and message text
- **Send responses** via Messenger API using `MESSENGER_PAGE_TOKEN`

### ChannelService (Unified)
Abstracts message sending:
- Receives channel, destination ID, and text
- Uses corresponding credentials per channel
- Reuses `Customer.channel_id` to map phones/PSIDs to existing customers

---

## Sales Agent & Closing Logic

### Aria with Ollama (Local LLM)
- Model: `qwen2.5:7b` (configurable via `OLLAMA_MODEL`)
- System prompt reinforced with **sales and closing** instructions:
  - Detect purchase intent ("lo quiero", "cómo compro", "hacer pedido")
  - Offer complementary products by category (e.g., socks with shoes)
  - **Proactive closing**: on purchase signals, request confirmation and generate order
  - Internal token format: `{{VENDIDO:product_id,cantidad}}` for sale detection

### Stripe Payment Links
- `StripeService` creates a `PaymentLink` per sale using `stripe.payment_links.create()`
- Sends the link via the channel after order confirmation
- Link points to a success URL configured in `.env`

### Stock Deduction
On detecting `{{VENDIDO:...}}`:
1. Create `Sale` record with `closed_by_ai=True`
2. `Product.stock -= quantity` (logic already exists in `ai_agent.py`)
3. Respond to customer with the Stripe payment link

---

## Environment Variables (.env)

```bash
# WhatsApp Business API
WHATSAPP_TOKEN=your_meta_token
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Facebook Messenger
MESSENGER_PAGE_TOKEN=your_page_token
MESSENGER_VERIFY_TOKEN=your_verify_token

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_SUCCESS_URL=https://yourdomain.com/payment-success

# Ollama (already exists)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b
```

---

## Database Changes

No schema changes required. The existing models already support:
- `Customer.channel` (enum: whatsapp, messenger, web, manual)
- `Customer.channel_id` (external ID for phone/PSID)
- `Conversation.channel` and `conversation_id` tracking
- `Sale.closed_by_ai` boolean
- `Product.stock` and `Product.reserved` fields

---

## Security

- Webhook verification: validate tokens on GET requests
- Rate limiting: reuse existing SlowAPI/Nginx rate limits
- Stripe webhook signature verification for payment confirmations (future enhancement)
- No sensitive data in webhook responses

---

## Error Handling

- Failed Ollama calls: retry once, then send fallback message
- Stripe link generation failure: log error, notify customer to retry
- Invalid webhook payload: return 400, log for debugging
- Customer not found: auto-create with channel metadata

---

## Files to Create/Modify

### New Files
- `backend/app/routers/webhooks.py` — WhatsApp + Messenger webhook handlers
- `backend/app/services/channel_service.py` — Unified message sending
- `backend/app/services/stripe_service.py` — Stripe payment link generation

### Modified Files
- `backend/app/services/ai_agent.py` — Enhance system prompt for sales closing, detect `{{VENDIDO}}` token
- `backend/app/main.py` — Register webhook router
- `backend/requirements.txt` — Add `stripe` dependency
- `.env.example` — Add new environment variables

---

## Success Criteria

1. Customer sends "quiero zapatos" via WhatsApp → Aria responds with options
2. Customer confirms purchase → Sale created, stock deducted, Stripe link sent
3. Same flow works via Messenger
4. Conversation and Sale records are correctly linked in DB
5. `closed_by_ai=True` on all AI-closed sales

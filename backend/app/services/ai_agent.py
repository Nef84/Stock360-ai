"""
AI Sales Agent Service — Aria
Calls Anthropic API with inventory context. Detects sales closure,
cross-sell opportunities, and escalation triggers.
"""
import anthropic
import httpx
import logging
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.inventory import Product, Conversation, Message, MessageSource, Sale, SaleStatus, ConversationStatus
from app.services.stripe_service import StripeService, StripeServiceError

logger = logging.getLogger("stock360.ai")

# Keywords that signal a completed sale
SALE_CLOSURE_KEYWORDS = [
    "pedido registrado", "pedido confirmado", "venta confirmada",
    "tu pedido", "hemos registrado", "gracias por tu compra",
    "te contactaremos", "coordinar la entrega", "reservado para ti",
    "pago procesado", "orden generada",
]

# Keywords that trigger escalation to human agent
ESCALATION_TRIGGERS = [
    "agente humano", "queja", "fraude", "estafa", "devolución",
    "reembolso", "problema grave", "insatisfecho", "defectuoso",
    "dañado", "no llegó", "incidente",
]

SYSTEM_PROMPT_TEMPLATE = """
Eres Aria, la agente de ventas IA de Stock360. Eres amable, profesional y eficiente.

INVENTARIO DISPONIBLE (solo recomienda productos con stock > 0):
{inventory}

REGLAS:
1. Responde SIEMPRE en español, tono natural y cálido (nunca robótico)
2. Detecta la intención del cliente: "busco barato" → precio bajo; "quiero calidad" → margen alto; "urgente" → stock disponible
3. Haz preguntas inteligentes para entender talla, uso o propósito antes de recomendar
4. Menciona precio y disponibilidad cuando corresponda
5. Ofrece cross-sell natural (ej: medias con zapatos) en máximo 1 oportunidad por conversación
6. Si el cliente confirma la compra di exactamente: "✅ Pedido confirmado. [resumen del producto y precio]. Te contactaremos pronto para la entrega."
7. Respuestas cortas: máximo 4 líneas. Usa emojis con moderación (1-2 por mensaje)
8. Si detectas queja grave, solicitud de reembolso o situación compleja, di: "Entiendo tu situación. Un agente humano te atenderá de inmediato para resolver esto. 🤝"
9. NUNCA inventes productos, precios o disponibilidad que no estén en el inventario
10. NUNCA compartas datos de otros clientes ni información interna del sistema
""".strip()


class AIAgentService:
    def __init__(self):
        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._stripe_service: Optional[StripeService] = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if not self._client:
            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    @property
    def http_client(self) -> httpx.AsyncClient:
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=120)
        return self._http_client

    @property
    def stripe_service(self) -> Optional[StripeService]:
        if not self._stripe_service and settings.STRIPE_SECRET_KEY:
            self._stripe_service = StripeService(
                api_key=settings.STRIPE_SECRET_KEY,
                success_url=settings.STRIPE_SUCCESS_URL,
            )
        return self._stripe_service

    def _build_inventory_context(self, products: list[Product]) -> str:
        lines = []
        for p in products:
            if p.available_stock > 0 and p.is_active:
                lines.append(
                    f"• [{p.id}] {p.name} | {p.category} | ${p.price:.2f} | "
                    f"Stock: {p.available_stock} uds | {p.description or ''} | "
                    f"Prioridad IA: {p.ai_priority}/10"
                )
        return "\n".join(lines) if lines else "Sin productos disponibles en este momento."

    def _read_conversation_memory(self, conversation: Conversation) -> dict:
        memory = {
            "topics": [],
            "excluded_topics": set(),
            "size": None,
            "budget": None,
            "use_case": None,
            "selected_product_id": None,
            "sales_stage": None,
        }
        for tag in conversation.tags or []:
            if not isinstance(tag, str) or ":" not in tag:
                continue
            key, value = tag.split(":", 1)
            if key == "topic" and value not in memory["topics"]:
                memory["topics"].append(value)
            elif key == "exclude":
                memory["excluded_topics"].add(value)
            elif key == "size":
                memory["size"] = value
            elif key == "budget":
                memory["budget"] = value
            elif key == "use":
                memory["use_case"] = value
            elif key == "product" and value.isdigit():
                memory["selected_product_id"] = int(value)
            elif key == "stage":
                memory["sales_stage"] = value
        return memory

    def _write_conversation_memory(self, conversation: Conversation, state: dict) -> None:
        preserved = [tag for tag in (conversation.tags or []) if isinstance(tag, str) and not tag.startswith(("topic:", "exclude:", "size:", "budget:", "use:", "product:", "stage:"))]
        memory_tags = [f"topic:{topic}" for topic in state.get("topics", [])[:4]]
        memory_tags += [f"exclude:{topic}" for topic in sorted(state.get("excluded_topics", set()))[:4]]
        if state.get("size"):
            memory_tags.append(f"size:{state['size']}")
        if state.get("budget"):
            memory_tags.append(f"budget:{state['budget']}")
        if state.get("use_case"):
            memory_tags.append(f"use:{state['use_case']}")
        if state.get("selected_product_id"):
            memory_tags.append(f"product:{state['selected_product_id']}")
        if state.get("sales_stage"):
            memory_tags.append(f"stage:{state['sales_stage']}")
        conversation.tags = preserved + memory_tags

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def _get_catalog_terms(self) -> dict[str, set[str]]:
        return {
            "calzado": {"zapato", "zapatos", "tenis", "zapatilla", "zapatillas", "running", "sneaker", "sneakers"},
            "medias": {"media", "medias", "calcetin", "calcetines"},
            "camisetas": {"camiseta", "camisetas", "shirt", "shirts", "playera", "playeras"},
            "shorts": {"short", "shorts", "bermuda", "bermudas"},
            "botellas": {"botella", "botellas", "termo", "termos", "tomatodo", "tomatodos"},
            "ropa_deportiva": {"ropa deportiva", "ropa", "deportiva", "gym", "entrenar"},
        }

    def _get_use_case_terms(self) -> dict[str, set[str]]:
        return {
            "running": {"correr", "running", "runner", "trotar"},
            "gym": {"gym", "gimnasio", "entrenar", "pesas", "crossfit"},
            "futbol": {"futbol", "fútbol", "cancha", "taquetes"},
            "casual": {"diario", "casual", "todos los dias", "todo el dia"},
            "senderismo": {"senderismo", "trail", "montana", "montaña", "outdoor"},
            "natacion": {"natacion", "natación", "piscina", "nadar"},
            "ciclismo": {"ciclismo", "bicicleta", "bici", "pedalear"},
        }

    def _extract_size(self, text: str) -> Optional[str]:
        normalized = self._normalize_text(text)
        match = re.search(r"\btalla\s+([a-z0-9]+)\b", normalized)
        if match:
            return match.group(1).upper()

        for alias in ["xs", "s", "m", "l", "xl", "xxl", "38", "39", "40", "41", "42", "43", "44", "45", "46", "12"]:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                return alias.upper()
        return None

    def _extract_budget_level(self, text: str) -> Optional[str]:
        normalized = self._normalize_text(text)
        if any(word in normalized for word in ["barato", "economico", "económico", "oferta", "accesible"]):
            return "budget"
        if any(word in normalized for word in ["premium", "mejor", "top", "alta gama", "calidad"]):
            return "premium"
        return None

    def _extract_use_case(self, text: str) -> Optional[str]:
        normalized = self._normalize_text(text)
        for use_case, aliases in self._get_use_case_terms().items():
            if any(alias in normalized for alias in aliases):
                return use_case
        return None

    def _build_conversation_state(self, conversation: Conversation, history: list[Message], current_text: str) -> dict:
        state = self._read_conversation_memory(conversation)

        customer_messages = [
            self._normalize_text(msg.content)
            for msg in history
            if msg.source == MessageSource.CUSTOMER and msg.content
        ]

        for msg in customer_messages[-8:] + [self._normalize_text(current_text)]:
            requested = self._detect_requested_topics(msg)
            excluded = self._detect_excluded_topics(msg)

            for topic in requested:
                if topic not in state["topics"] and topic not in excluded:
                    state["topics"].append(topic)

            state["excluded_topics"].update(excluded)

            size = self._extract_size(msg)
            if size:
                state["size"] = size

            budget = self._extract_budget_level(msg)
            if budget:
                state["budget"] = budget

            use_case = self._extract_use_case(msg)
            if use_case:
                state["use_case"] = use_case

        state["topics"] = [topic for topic in state["topics"] if topic not in state["excluded_topics"]]
        return state

    def _product_matches_size(self, product: Product, size: Optional[str]) -> bool:
        if not size:
            return True
        haystack = self._normalize_text(f"{product.name} {product.description or ''}")
        return size.lower() in haystack

    def _score_product(self, product: Product, topic: Optional[str], state: dict, query: str) -> float:
        score = float(product.ai_priority) + max(0.0, 25.0 - product.price / 10.0)
        haystack = self._normalize_text(f"{product.name} {product.category} {product.description or ''}")
        query_words = set(re.findall(r"[a-zA-Záéíóúñ0-9]+", self._normalize_text(query)))

        if topic:
            for alias in self._get_catalog_terms().get(topic, set()):
                if alias in haystack:
                    score += 14

        use_case = state.get("use_case")
        if use_case:
            for alias in self._get_use_case_terms().get(use_case, set()):
                if alias in haystack:
                    score += 8

        if state.get("size") and self._product_matches_size(product, state["size"]):
            score += 10

        if state.get("budget") == "budget":
            score += max(0.0, 20.0 - product.price / 4.0)
        elif state.get("budget") == "premium":
            score += product.price / 6.0

        for word in query_words:
            if len(word) > 2 and word in haystack:
                score += 2

        return score

    def _select_products(self, products: list[Product], topic: Optional[str], state: dict, query: str) -> list[Product]:
        if not products:
            return []
        scored = sorted(
            products,
            key=lambda item: self._score_product(item, topic, state, query),
            reverse=True,
        )

        if state.get("size"):
            exact = [product for product in scored if self._product_matches_size(product, state["size"])]
            if exact:
                return exact[:4]

        return scored[:4]

    def _topic_label(self, topic: str) -> str:
        return {
            "calzado": "zapatos",
            "medias": "calcetines",
            "camisetas": "camisetas",
            "shorts": "shorts",
            "botellas": "botellas",
            "ropa_deportiva": "ropa deportiva",
        }.get(topic, topic.replace("_", " "))

    def _compose_recommendation(self, topic: str, selected: list[Product], state: dict) -> str:
        label = self._topic_label(topic)
        if not selected:
            return self._unavailable_topic_response(topic)

        primary = selected[0]
        secondary = selected[1] if len(selected) > 1 else None
        mention_size = (
            f" y tomé en cuenta la talla {state['size']}"
            if state.get("size") else ""
        )
        compare_text = (
            f" También te puedo comparar con {secondary.name} en ${secondary.price:.2f}."
            if secondary else ""
        )

        if state.get("budget") == "budget":
            return (
                f"Sí, en {label} te recomiendo {primary.name} en ${primary.price:.2f}{mention_size}. "
                f"Tengo {primary.available_stock} unidades disponibles.{compare_text}"
            )

        if state.get("budget") == "premium":
            return (
                f"Si buscas algo mejor en {label}, me iría por {primary.name} en ${primary.price:.2f}{mention_size}. "
                f"Hay {primary.available_stock} disponibles.{compare_text}"
            )

        return (
            f"Sí, en {label} te puede funcionar {primary.name} en ${primary.price:.2f}{mention_size}. "
            f"Hay {primary.available_stock} disponibles.{compare_text}"
        )

    def _compose_multi_topic_response(self, state: dict, products: list[Product], query: str) -> Optional[str]:
        topics = state.get("topics", [])
        if not topics:
            return None

        lines: list[str] = []
        for topic in topics[:3]:
            topic_products = self._find_products_for_topic(topic, products)
            selected = self._select_products(topic_products, topic, state, query)
            if selected:
                product = selected[0]
                lines.append(f"{self._topic_label(topic).capitalize()}: {product.name} por ${product.price:.2f}")
            else:
                lines.append(f"{self._topic_label(topic).capitalize()}: ahorita no veo inventario disponible")

        if len(lines) == 1:
            return None

        return "Claro. Te resumo rápido lo que sí tengo:\n" + "\n".join(lines[:3])

    def _detect_requested_topics(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        topics: set[str] = set()
        for topic, aliases in self._get_catalog_terms().items():
            if any(alias in normalized for alias in aliases):
                topics.add(topic)
        return topics

    def _detect_excluded_topics(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        exclusions: set[str] = set()
        for topic, aliases in self._get_catalog_terms().items():
            for alias in aliases:
                if f"no busco {alias}" in normalized or f"no quiero {alias}" in normalized:
                    exclusions.add(topic)
                if f"sin {alias}" in normalized:
                    exclusions.add(topic)
        return exclusions

    def _find_active_topic(self, history: list[Message], current_text: str) -> Optional[str]:
        excluded_topics = self._detect_excluded_topics(current_text)

        current_topics = self._detect_requested_topics(current_text) - excluded_topics
        if current_topics:
            return next(iter(current_topics))

        for msg in reversed(history):
            if msg.source != MessageSource.CUSTOMER or not msg.content:
                continue
            msg_topics = self._detect_requested_topics(msg.content) - self._detect_excluded_topics(msg.content)
            msg_topics -= excluded_topics
            if msg_topics:
                return next(iter(msg_topics))
        return None

    def _find_products_for_topic(self, topic: str, products: list[Product]) -> list[Product]:
        aliases = self._get_catalog_terms().get(topic, set())
        matches: list[Product] = []
        for product in products:
            haystack = self._normalize_text(
                f"{product.name} {product.category} {product.description or ''}"
            )
            if any(alias in haystack for alias in aliases):
                matches.append(product)
        return sorted(matches, key=lambda item: (item.ai_priority, item.price), reverse=True)

    def _unavailable_topic_response(self, topic: str) -> str:
        labels = {
            "botellas": "botellas para agua",
            "camisetas": "camisetas",
            "shorts": "shorts",
            "ropa_deportiva": "ropa deportiva",
            "calzado": "calzado",
            "medias": "medias",
        }
        label = labels.get(topic, topic.replace("_", " "))
        return (
            f"Te entiendo. En este momento no veo {label} en el inventario disponible. "
            "Prefiero decírtelo claro antes que ofrecerte algo que no corresponde. "
            "Si quieres, te muestro lo que sí hay ahorita o dejamos registrada tu búsqueda."
        )

    def _recent_customer_messages(self, history: list[Message]) -> list[str]:
        return [
            self._normalize_text(msg.content)
            for msg in history
            if msg.source == MessageSource.CUSTOMER and msg.content
        ][-6:]

    def _is_first_customer_touch(self, history: list[Message]) -> bool:
        customer_count = sum(1 for msg in history if msg.source == MessageSource.CUSTOMER and msg.content)
        return customer_count <= 1

    def _find_products_for_query(self, query: str, products: list[Product]) -> list[Product]:
        query_words = set(re.findall(r"[a-zA-Záéíóúñ0-9]+", self._normalize_text(query)))
        if not query_words:
            return []

        matches: list[tuple[int, Product]] = []
        for product in products:
            haystack = self._normalize_text(
                f"{product.name} {product.category} {product.description or ''}"
            )
            score = sum(1 for word in query_words if len(word) > 2 and word in haystack)
            if score > 0:
                matches.append((score, product))

        matches.sort(key=lambda item: (item[0], item[1].ai_priority, item[1].price), reverse=True)
        return [product for _, product in matches]

    def _get_selected_product(self, state: dict, products: list[Product]) -> Optional[Product]:
        selected_id = state.get("selected_product_id")
        if not selected_id:
            return None
        return next((product for product in products if product.id == selected_id), None)

    def _remember_product(self, state: dict, product: Optional[Product], stage: str = "considering") -> None:
        if not product:
            return
        state["selected_product_id"] = product.id
        state["sales_stage"] = stage

    def _is_purchase_signal(self, text: str) -> bool:
        signals = [
            "me lo llevo", "lo quiero", "lo compro", "dame ese", "dame esos",
            "esta bien", "está bien", "me quedo con", "listo", "dale",
            "ok", "perfecto", "confirmo", "hagamoslo", "hagámoslo",
        ]
        return any(signal in text for signal in signals)

    def _is_payment_or_delivery_question(self, text: str) -> bool:
        triggers = [
            "envio", "envío", "enviarlo", "enviarlos", "domicilio",
            "entrega", "retiro", "pago", "pagar", "transferencia",
            "tarjeta", "contra entrega", "deposito", "depósito",
        ]
        return any(trigger in text for trigger in triggers)

    def _is_variant_question(self, text: str) -> bool:
        triggers = [
            "color", "colores", "tienen en", "hay en", "manejan en",
            "en color", "en blanco", "en negra", "en negro", "en azul",
        ]
        return any(trigger in text for trigger in triggers)

    def _find_variant_products(
        self,
        selected_product: Optional[Product],
        active_topic: Optional[str],
        products: list[Product],
        query: str,
    ) -> list[Product]:
        if not active_topic:
            return []
        base_candidates = self._find_products_for_topic(active_topic, products)
        query_matches = self._find_products_for_query(query, base_candidates)
        if not selected_product:
            return query_matches

        brand_hint = self._normalize_text(selected_product.name).split(" ")[0]
        brand_matches = [
            product for product in query_matches
            if brand_hint and brand_hint in self._normalize_text(product.name)
        ]
        return brand_matches or query_matches

    def _demo_response(
        self,
        conversation: Conversation,
        customer_message: str,
        products: list[Product],
        history: Optional[list[Message]] = None,
        state: Optional[dict] = None,
    ) -> str:
        text = self._normalize_text(customer_message)
        if self._detect_escalation(text):
            return "Entiendo tu situación. Un agente humano te atenderá de inmediato para resolver esto. 🤝"

        if not products:
            return "En este momento no tengo productos disponibles. Si quieres, te tomo el dato y te escribimos apenas haya inventario."

        history = history or []
        recent_customer_messages = self._recent_customer_messages(history)
        prior_customer_context = " ".join(recent_customer_messages[:-1])
        state = state or self._build_conversation_state(conversation, history, text)
        active_topic = state["topics"][0] if state["topics"] else self._find_active_topic(history, text)
        selected_product = self._get_selected_product(state, products)

        affordable = min(products, key=lambda p: p.price)
        premium = max(products, key=lambda p: (p.ai_priority, p.price))
        premium_alt = next((p for p in products if p.id != affordable.id), premium)
        running_pick = next(
            (p for p in products if any(word in (p.description or "").lower() for word in ["running", "correr", "deporte"])),
            premium_alt,
        )
        matched_products = self._find_products_for_query(f"{prior_customer_context} {text}", products)
        top_match = matched_products[0] if matched_products else None
        topic_products = self._find_products_for_topic(active_topic, products) if active_topic else []
        topic_selected = self._select_products(topic_products, active_topic, state, f"{prior_customer_context} {text}") if active_topic else []
        topic_match = topic_selected[0] if topic_selected else None

        if len(state["topics"]) > 1 and any(word in text for word in ["tambien", "también", "y", "ademas", "además"]):
            multi_topic_response = self._compose_multi_topic_response(state, products, f"{prior_customer_context} {text}")
            if multi_topic_response:
                return multi_topic_response

        if active_topic and not topic_products:
            return self._unavailable_topic_response(active_topic)

        if selected_product and self._is_purchase_signal(text):
            self._remember_product(state, selected_product, "won")
            return (
                f"✅ Pedido confirmado. {selected_product.name} por ${selected_product.price:.2f}. "
                "Te contactaremos pronto para la entrega."
            )

        if selected_product and self._is_variant_question(text):
            variant_products = self._find_variant_products(
                selected_product,
                active_topic,
                products,
                f"{selected_product.name} {prior_customer_context} {text}",
            )
            if variant_products:
                selected_product = variant_products[0]
                self._remember_product(state, selected_product, "considering")
                return (
                    f"Sí, dentro de esa línea te puedo ofrecer {selected_product.name} en ${selected_product.price:.2f}. "
                    f"Tengo {selected_product.available_stock} disponibles. "
                    "Si te parece, te lo dejo reservado de una vez."
                )

        if selected_product and self._is_payment_or_delivery_question(text):
            self._remember_product(state, selected_product, "closing")
            return (
                f"Sí, con {selected_product.name} te podemos coordinar envío o entrega, y normalmente se puede pagar por transferencia o contra entrega según zona. "
                f"Lo importante es que sí tengo {selected_product.available_stock} unidades disponibles. "
                "Si te parece bien, te lo dejo confirmado ahora mismo."
            )

        if topic_match:
            self._remember_product(state, topic_match, "considering")
            if active_topic == "calzado" and any(word in text for word in ["talla", "medium", "small", "large", "m", "s", "l", "xl", "que tallas", "tallas", "soy talla"]):
                return (
                    f"Perfecto, para calzado te puedo orientar con {topic_match.name} en ${topic_match.price:.2f}. "
                    f"Veo {topic_match.available_stock} unidades disponibles"
                    + (f" y esta opción sí coincide con la talla {state['size']}. Si te gusta, te la puedo dejar apartada." if state.get("size") else ". Si te gusta, te la puedo dejar apartada.")
                )

            return self._compose_recommendation(active_topic, topic_selected, state)

        if top_match and not active_topic:
            self._remember_product(state, top_match, "considering")
            if any(word in text for word in ["talla", "medium", "small", "large", "m", "s", "l", "xl"]):
                return (
                    f"Claro. Del modelo {top_match.name} puedo ayudarte a validar talla y disponibilidad. "
                    f"Por ahora tengo {top_match.available_stock} unidades. "
                    "Si me dices qué talla usas normalmente, te oriento mejor y te la puedo dejar lista."
                )

        if any(word in text for word in ["barato", "econ", "precio", "oferta"]):
            self._remember_product(state, affordable, "considering")
            return (
                f"Claro, si buscas algo accesible te diria que veas {affordable.name}, que esta en ${affordable.price:.2f}. "
                f"Tenemos {affordable.available_stock} unidades disponibles. "
                f"Si quieres, tambien te comparo esa opcion con {premium_alt.name}, que ya sube un poco mas de nivel. "
                "Si te encaja, te lo puedo dejar reservado."
            )

        if any(word in text for word in ["calidad", "premium", "mejor", "recomiendas"]):
            self._remember_product(state, premium_alt, "considering")
            return (
                f"Si quieres algo mas completo, me iria por {premium_alt.name} en ${premium_alt.price:.2f}. "
                f"Hay {premium_alt.available_stock} disponibles y se siente como una opcion mas fuerte dentro del catalogo. "
                "Si te gusta esa opcion, te la puedo dejar apartada ahora mismo."
            )

        if any(word in text for word in ["correr", "running", "gym", "entrenar", "deporte"]):
            self._remember_product(state, running_pick, "considering")
            return (
                f"Perfecto, para ese uso te recomendaria {running_pick.name} por ${running_pick.price:.2f}. "
                f"Ahorita hay {running_pick.available_stock} unidades. "
                "Si te gusta esa, te la puedo dejar reservada; y si prefieres, también te separo por calzado, ropa o accesorios."
            )

        if self._is_first_customer_touch(history) and any(word in text for word in ["hola", "buenas", "buenos dias", "buenas tardes", "informacion", "información"]):
            return (
                "Hola, soy Sofi, tu asistente digital de ventas, y estoy aquí para ayudarte a encontrar y comprar la mejor opción para ti. "
                f"Ahorita puedo orientarte con opciones como {premium_alt.name} desde ${premium_alt.price:.2f} "
                f"o {affordable.name} en ${affordable.price:.2f}. "
                "Si me dices qué estás buscando, te recomiendo algo puntual y te acompaño hasta dejar tu pedido listo."
            )

        if any(word in text for word in ["comprar", "llevo", "quiero", "pedido", "confirmo"]):
            self._remember_product(state, selected_product or premium_alt, "won")
            return (
                f"✅ Pedido confirmado. {(selected_product or premium_alt).name} por ${(selected_product or premium_alt).price:.2f}. "
                "Te contactaremos pronto para la entrega."
            )

        return (
            "Claro, te ayudo. "
            f"Por ejemplo, tengo {affordable.name} en ${affordable.price:.2f} y {premium_alt.name} en ${premium_alt.price:.2f}. "
            "Si me dices si lo quieres para uso diario, para correr o si buscas algo mas premium, te guio mejor y te dejo una opcion lista para compra."
        )

    async def _ollama_response(self, system_prompt: str, messages: list[dict]) -> str:
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": False,
            "options": {
                "temperature": settings.AI_TEMPERATURE,
            },
        }
        response = await self.http_client.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()

    def _detect_sale(self, ai_response: str) -> bool:
        text = ai_response.lower()
        return any(kw in text for kw in SALE_CLOSURE_KEYWORDS)

    def _detect_escalation(self, message: str) -> bool:
        text = message.lower()
        return any(kw in text for kw in ESCALATION_TRIGGERS)

    def _extract_product_from_response(
        self, response: str, products: list[Product]
    ) -> Optional[Product]:
        """Try to identify which product was sold from the AI response."""
        response_lower = response.lower()
        # Sort by name length descending to prefer more specific matches
        for p in sorted(products, key=lambda x: len(x.name), reverse=True):
            if p.name.lower() in response_lower:
                return p
        return None

    async def generate_response(
        self,
        db: AsyncSession,
        conversation: Conversation,
        history: list[Message],
        customer_message: str,
    ) -> dict:
        """
        Generate AI response for a customer message.
        Returns: {response_text, sale_detected, escalation_detected, product}
        """
        # Load available products
        result = await db.execute(
            select(Product).where(Product.is_active == True, Product.stock > 0)
            .order_by(Product.ai_priority.desc())
        )
        products = result.scalars().all()

        inventory_text = self._build_inventory_context(products)
        system_prompt  = SYSTEM_PROMPT_TEMPLATE.format(inventory=inventory_text)
        state = self._build_conversation_state(conversation, history, customer_message)

        # Build message history for API (skip system messages)
        api_messages = []
        for msg in history[-20:]:   # limit context window to last 20 messages
            if msg.source == MessageSource.CUSTOMER:
                api_messages.append({"role": "user", "content": msg.content})
            elif msg.source in (MessageSource.AI,):
                api_messages.append({"role": "assistant", "content": msg.content})

        api_messages.append({"role": "user", "content": customer_message})

        provider = settings.AI_PROVIDER.lower().strip()
        use_demo_mode = (
            provider == "demo"
            or (provider == "anthropic" and (
                not settings.ANTHROPIC_API_KEY
                or settings.ANTHROPIC_API_KEY.startswith("dummy")
            ))
        )

        if provider == "ollama":
            try:
                logger.info("Using Ollama provider with model %s", settings.OLLAMA_MODEL)
                ai_text = await self._ollama_response(system_prompt, api_messages)
            except httpx.HTTPError as exc:
                logger.warning("Falling back to demo AI because Ollama request failed: %s", exc)
                ai_text = self._demo_response(conversation, customer_message, list(products), history, state)
        elif use_demo_mode:
            logger.info("Using demo AI fallback")
            ai_text = self._demo_response(conversation, customer_message, list(products), history, state)
        else:
            try:
                logger.info("Using Anthropic provider with model %s", settings.AI_MODEL)
                response = await self.client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=settings.AI_MAX_TOKENS,
                    system=system_prompt,
                    messages=api_messages,
                )
                ai_text = response.content[0].text
            except anthropic.AuthenticationError as exc:
                logger.warning("Falling back to demo AI because Anthropic auth failed: %s", exc)
                ai_text = self._demo_response(conversation, customer_message, list(products), history, state)

        # Analysis
        self._write_conversation_memory(conversation, state)
        sale_detected      = self._detect_sale(ai_text)
        escalation_detected = self._detect_escalation(customer_message) or self._detect_escalation(ai_text)
        matched_product     = self._extract_product_from_response(ai_text, list(products)) if sale_detected else None

        # Generate Stripe payment link on sale
        stripe_link = None
        if sale_detected and matched_product and self.stripe_service:
            try:
                stripe_link = self.stripe_service.create_payment_link(
                    product_name=matched_product.name,
                    amount=int(matched_product.price * 100),
                    quantity=1,
                    metadata={
                        "conversation_id": str(conversation.id),
                        "product_id": str(matched_product.id),
                    },
                )
                ai_text += f"\n\n💳 Paga aquí: {stripe_link}"
            except StripeServiceError as exc:
                logger.error(f"Failed to generate Stripe link: {exc}")

        return {
            "response_text":       ai_text,
            "sale_detected":       sale_detected,
            "escalation_detected": escalation_detected,
            "product":             matched_product,
            "stripe_link":         stripe_link,
        }

    async def create_sale_record(
        self,
        db: AsyncSession,
        conversation: Conversation,
        product: Product,
        quantity: int = 1,
    ) -> Sale:
        """Persist a sale and adjust stock."""
        sale = Sale(
            conversation_id=conversation.id,
            product_id=product.id,
            customer_id=conversation.customer_id,
            quantity=quantity,
            unit_price=product.price,
            total=product.price * quantity,
            status=SaleStatus.PENDING,
            closed_by_ai=True,
        )
        db.add(sale)

        # Decrement stock
        product.stock = max(0, product.stock - quantity)

        await db.flush()
        return sale


ai_agent = AIAgentService()

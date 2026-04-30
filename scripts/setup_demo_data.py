import asyncio
import random
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.inventory import Channel, Conversation, ConversationStatus, Customer, Product


BRANDS = [
    "Nike", "Adidas", "Puma", "Under Armour", "Reebok", "New Balance", "Asics", "Mizuno",
    "Wilson", "Head", "Spalding", "Molten", "Yonex", "Everlast", "Speedo", "Arena",
    "CamelBak", "HydroPeak", "ThermoSport", "FitCore",
]

PRODUCT_LINES = [
    ("Calzado", "Tenis Running", "Amortiguacion reactiva para entreno y uso diario", (48, 145)),
    ("Calzado", "Tenis Trail", "Suela con agarre para senderos y exteriores", (58, 165)),
    ("Calzado", "Taquetes Futbol", "Estabilidad y traccion para cancha", (42, 130)),
    ("Ropa", "Camiseta Dry Fit", "Tela transpirable para entrenamientos intensos", (16, 45)),
    ("Ropa", "Short Deportivo", "Ligero, comodo y de secado rapido", (14, 38)),
    ("Ropa", "Legging Performance", "Compresion media para gym y running", (22, 55)),
    ("Ropa", "Chaqueta Rompeviento", "Proteccion ligera para clima cambiante", (28, 74)),
    ("Accesorios", "Botella Termica", "Mantiene la bebida fria por horas", (10, 32)),
    ("Accesorios", "Mochila Training", "Compartimentos para gym y laptop", (24, 68)),
    ("Accesorios", "Medias Tecnicas", "Tejido antihumedad y ajuste anatomico", (8, 22)),
    ("Accesorios", "Gorra Sport", "Proteccion solar y ajuste comodo", (9, 26)),
    ("Accesorios", "Cangurera Runner", "Ideal para llaves, celular y geles", (12, 34)),
    ("Fitness", "Mancuerna Ajustable", "Entrenamiento funcional en casa", (32, 95)),
    ("Fitness", "Banda de Resistencia", "Ideal para movilidad y fuerza", (7, 21)),
    ("Fitness", "Mat de Yoga", "Superficie antideslizante y acolchada", (18, 48)),
    ("Fitness", "Cuerda de Saltar", "Rodamientos suaves para cardio", (8, 24)),
    ("Ciclismo", "Casco Urbano", "Ventilacion y ajuste seguro", (26, 78)),
    ("Ciclismo", "Guantes Ciclismo", "Acolchado para recorridos largos", (12, 30)),
    ("Natacion", "Gafas Natacion", "Vision clara y antiempanante", (11, 29)),
    ("Outdoor", "Bolso Hidratacion", "Capacidad extra para rutas largas", (29, 72)),
]

SIZES = ["XS", "S", "M", "L", "XL", "Unica", "38", "39", "40", "41", "42", "43", "44"]
COLORS = ["Negro", "Azul", "Rojo", "Gris", "Verde", "Blanco", "Naranja", "Morado"]
CUSTOMER_NAMES = [
    "Valeria Quintanilla", "Mateo Rivera", "Daniela Flores", "Andres Mejia", "Camila Pineda",
    "Sebastian Ayala", "Gabriela Cruz", "Javier Escobar", "Paola Alvarado", "Fernando Ruiz",
    "Lucia Menendez", "Oscar Bonilla", "Mariana Araujo", "Kevin Portillo", "Alejandra Rivas",
    "Bryan Aguilar", "Natalia Marroquin", "Ernesto Campos", "Carla Molina", "Samuel Hernandez",
    "Andrea Orellana", "Ricardo Sorto", "Isabella Palma", "Mauricio Renderos", "Daniela Arce",
]


def build_products(start_index: int, count: int) -> list[Product]:
    rng = random.Random(360)
    products: list[Product] = []

    for index in range(start_index, start_index + count):
        category, product_type, description, (min_price, max_price) = PRODUCT_LINES[index % len(PRODUCT_LINES)]
        brand = BRANDS[index % len(BRANDS)]
        color = COLORS[index % len(COLORS)]
        size = SIZES[index % len(SIZES)]
        price = round(min_price + ((index * 7) % max(1, (max_price - min_price))), 2)
        cost = round(price * rng.uniform(0.42, 0.68), 2)
        margin_pct = round(((price - cost) / price) * 100, 2)
        stock = 6 + (index * 3) % 55
        ai_priority = 5 + (index % 6)
        sku = f"STK-{category[:3].upper()}-{index + 1:04d}"
        name = f"{brand} {product_type} {color} {size}"
        full_description = f"{description}. Color {color}. Talla {size}. Linea demo #{index + 1}."
        products.append(
            Product(
                name=name,
                category=category,
                description=full_description,
                price=price,
                cost=cost,
                stock=stock,
                margin_pct=margin_pct,
                sku=sku,
                ai_priority=ai_priority,
                is_active=True,
            )
        )
    return products


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing_products = (await db.execute(select(Product))).scalars().all()
        target_total = 1000
        missing = max(0, target_total - len(existing_products))

        if missing:
            for product in build_products(len(existing_products), missing):
                db.add(product)

        now = datetime.now(timezone.utc)
        conversations = (await db.execute(select(Conversation))).scalars().all()
        for conversation in conversations:
            conversation.status = ConversationStatus.CLOSED
            conversation.ai_active = False
            conversation.closed_at = conversation.closed_at or now
            conversation.updated_at = now

        new_customers: list[Customer] = []
        for idx, name in enumerate(CUSTOMER_NAMES, start=1):
            customer = Customer(
                name=name,
                channel=Channel.WHATSAPP,
                phone=f"+5037000{idx:04d}",
                email=f"demo{idx:02d}@stock360.com",
            )
            db.add(customer)
            new_customers.append(customer)

        await db.flush()

        for customer in new_customers:
            conversation = Conversation(
                customer_id=customer.id,
                channel=Channel.WHATSAPP,
                status=ConversationStatus.OPEN,
                ai_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(conversation)

        await db.commit()
        print(
            f"Demo data ready: total_products={len(existing_products) + missing}, "
            f"closed_conversations={len(conversations)}, new_conversations={len(new_customers)}"
        )


if __name__ == "__main__":
    asyncio.run(main())

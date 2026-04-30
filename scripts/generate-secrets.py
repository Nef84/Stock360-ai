#!/usr/bin/env python3
"""
Genera valores seguros para el archivo .env
Ejecutar: python scripts/generate-secrets.py
"""
import secrets
import string

def gen_token(n=64):
    return secrets.token_urlsafe(n)

def gen_password(n=20):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(n))

print("=" * 60)
print("  Stock360 AI — Valores seguros para .env")
print("=" * 60)
print(f"\nSECRET_KEY={gen_token(64)}")
print(f"POSTGRES_PASSWORD={gen_password(24)}")
print(f"REDIS_PASSWORD={gen_password(20)}")
print(f"ADMIN_PASSWORD={gen_password(16)}")
print(f"WHATSAPP_VERIFY_TOKEN={gen_token(32)}")
print(f"MESSENGER_VERIFY_TOKEN={gen_token(32)}")
print("\n⚠️  Copia estos valores en tu .env. No los compartas.")

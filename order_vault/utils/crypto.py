# utils/crypto.py
import base64, os
from cryptography.fernet import Fernet

def get_fernet():
    key = os.environ["TENANT_SECRET_KEY"]  # 32 urlsafe base64 bytes
    return Fernet(key)

def enc(plaintext: str) -> bytes:
    return get_fernet().encrypt(plaintext.encode("utf-8"))

def dec(ciphertext: bytes) -> str:
    return get_fernet().decrypt(ciphertext).decode("utf-8")

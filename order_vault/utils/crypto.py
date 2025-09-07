# utils/crypto.py
import os
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, g

_fernet = None  # cached singleton

def _load_key() -> str:
    # Prefer Flask config, fallback to env
    key = None
    try:
        key = current_app.config.get("TENANT_SECRET_KEY")
    except RuntimeError:
        # current_app may not be active (e.g., CLI context)
        pass
    if not key:
        key = os.environ.get("TENANT_SECRET_KEY")

    if not key:
        raise RuntimeError(
            "TENANT_SECRET_KEY is not set. Generate one with "
            "`from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())` "
            "and set it as an environment variable or app config."
        )
    return key

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = _load_key()
        _fernet = Fernet(key)
    return _fernet

def enc(plaintext: str) -> bytes:
    return get_fernet().encrypt(plaintext.encode("utf-8"))

def dec(ciphertext: bytes) -> str:
    return get_fernet().decrypt(ciphertext).decode("utf-8")

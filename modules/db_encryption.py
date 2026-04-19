import os
from cryptography.fernet import Fernet
from typing import Optional

KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", ".db_key")

def _get_key() -> bytes:
    """Load the encryption key or generate a new one if it doesn't exist."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

_fernet = None

def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_key())
    return _fernet

def encrypt_data(data: str) -> bytes:
    """Encrypt a string payload and return raw bytes."""
    f = _get_fernet()
    return f.encrypt(data.encode("utf-8"))

def decrypt_data(data: bytes) -> str:
    """Decrypt raw bytes and return the original string payload."""
    f = _get_fernet()
    return f.decrypt(data).decode("utf-8")

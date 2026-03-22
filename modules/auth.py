"""
Simple user authentication for the web edition.
Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib — no extra deps).
Users are stored in data/users.json.
"""

import hashlib
import json
import os
import secrets

_BASE = os.path.dirname(__file__)
USERS_FILE = os.path.normpath(os.path.join(_BASE, "..", "data", "users.json"))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_users(users: dict) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash(password: str, salt: str | None = None):
    """Return (salt, hex-digest). Pass existing salt to verify."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 200_000
    ).hex()
    return salt, digest


# ── Public API ────────────────────────────────────────────────────────────────

def ensure_default_admin() -> bool:
    """Create default admin account if no users exist. Returns True if created."""
    users = _load_users()
    if users:
        return False
    salt, hashed = _hash("admin123")
    _save_users({"admin": {"salt": salt, "password": hashed, "role": "admin"}})
    return True


def authenticate(username: str, password: str) -> bool:
    users = _load_users()
    user  = users.get(username)
    if not user:
        return False
    _, hashed = _hash(password, user["salt"])
    return hashed == user["password"]


def get_user_role(username: str) -> str:
    return _load_users().get(username, {}).get("role", "user")


def list_users() -> list:
    return [
        {"username": k, "role": v.get("role", "user")}
        for k, v in _load_users().items()
    ]


def create_user(username: str, password: str, role: str = "user"):
    """Returns (True, None) on success or (False, error_message)."""
    if not username or not password:
        return False, "Username and password are required"
    users = _load_users()
    if username in users:
        return False, "Username already exists"
    salt, hashed = _hash(password)
    users[username] = {"salt": salt, "password": hashed, "role": role}
    _save_users(users)
    return True, None


def change_password(username: str, new_password: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    salt, hashed = _hash(new_password)
    users[username]["salt"]     = salt
    users[username]["password"] = hashed
    _save_users(users)
    return True


def delete_user(username: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    del users[username]
    _save_users(users)
    return True

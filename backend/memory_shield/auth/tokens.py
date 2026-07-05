"""Token encryption for OAuth credentials at rest."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.getenv("OAUTH_TOKEN_FERNET_KEY", "")
    if not key:
        # Dev-only fallback — generate once and set in prod
        key = Fernet.generate_key().decode()
        os.environ["OAUTH_TOKEN_FERNET_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(text: str) -> bytes:
    if not text:
        return b""
    return _fernet().encrypt(text.encode())


def decrypt(blob: bytes) -> str:
    if not blob:
        return ""
    try:
        return _fernet().decrypt(blob).decode()
    except InvalidToken:
        return ""

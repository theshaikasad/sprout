"""Firebase ID token verification."""

from __future__ import annotations

import json
import os
from typing import Any

_firebase_app = None


def firebase_configured() -> bool:
    return bool(
        os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("FIREBASE_PROJECT_ID")
    )


def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return

    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        cred = credentials.ApplicationDefault()
    _firebase_app = firebase_admin.initialize_app(cred)


def verify_id_token(token: str) -> dict[str, Any]:
    _init_firebase()
    from firebase_admin import auth

    return auth.verify_id_token(token)

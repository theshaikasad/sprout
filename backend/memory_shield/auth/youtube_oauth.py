"""Server-side Google OAuth for YouTube + Analytics API (refresh tokens)."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from .tokens import decrypt, encrypt

CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://api.sprout.asad.codes/auth/youtube/callback",
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

TOKEN_URL = "https://oauth2.googleapis.com/token"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true"


def oauth_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET)


def auth_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_code(code: str) -> dict:
    data = urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def refresh_access_token(refresh_token: str) -> dict:
    data = urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_channel_info(access_token: str) -> dict:
    req = urllib.request.Request(
        CHANNELS_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    item = (data.get("items") or [None])[0]
    if not item:
        raise ValueError("no channel found for this Google account")
    snippet, stats = item["snippet"], item.get("statistics", {})
    custom = snippet.get("customUrl", "")
    handle = f"@{custom}" if custom and not custom.startswith("@") else custom
    return {
        "channel_id": item["id"],
        "title": snippet["title"],
        "avatar": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        "subscribers": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "handle": handle,
    }


def tokens_to_encrypted(tokens: dict) -> tuple[bytes, bytes, datetime | None]:
    access = encrypt(tokens.get("access_token", ""))
    refresh = encrypt(tokens.get("refresh_token", ""))
    expires = None
    if tokens.get("expires_in"):
        expires = datetime.now(timezone.utc) + timedelta(seconds=int(tokens["expires_in"]))
    return access, refresh, expires


def access_token_from_row(access_enc: bytes, refresh_enc: bytes, expires_at) -> str:
    """Return valid access token, refreshing if needed."""
    if expires_at and expires_at > datetime.now(timezone.utc):
        tok = decrypt(access_enc)
        if tok:
            return tok
    refresh = decrypt(refresh_enc)
    if not refresh:
        raise ValueError("no refresh token — reconnect YouTube")
    tokens = refresh_access_token(refresh)
    return tokens["access_token"]

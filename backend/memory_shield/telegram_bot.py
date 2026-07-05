"""Telegram bot — per-user linking + ambient nudges."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import urllib.request

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_LINK_SECRET
from .db.repos import get_user_by_telegram_chat
from .db.sync_session import sync_session
from .db.models import TelegramPollState, User
from .lifecycle import save_idea

SCRIPTED_NUDGE = (
    "🌱 Your last video is beating your trailing baseline on retention — "
    "people are staying. Want two ways to hold them even longer?"
)


def _api(method: str, payload: dict | None = None) -> dict | None:
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"telegram_bot: {method} failed — {e}")
        return None


def make_link_token(uid: str) -> str:
    ts = int(time.time())
    sig = hmac.new(
        TELEGRAM_LINK_SECRET.encode(),
        f"{uid}:{ts}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{uid}_{ts}_{sig}"


def verify_link_token(token: str) -> str | None:
    parts = token.split("_")
    if len(parts) < 3:
        return None
    uid, ts_str, sig = parts[0], parts[1], parts[2]
    if int(time.time()) - int(ts_str) > 900:
        return None
    expected = hmac.new(
        TELEGRAM_LINK_SECRET.encode(),
        f"{uid}:{ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return uid if hmac.compare_digest(sig, expected) else None


def link_telegram(uid: str, chat_id: str) -> None:
    with sync_session() as session:
        u = session.get(User, uid)
        if u:
            u.telegram_chat_id = chat_id
            session.add(u)
            session.commit()


def send_message(text: str, chat_id: str = "") -> bool:
    if not chat_id:
        return False
    result = _api("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(result and result.get("ok"))


def handle_update(update: dict) -> tuple[str, str]:
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id") or "")
    text = (msg.get("text") or "").strip()

    if text.lower().startswith("/start link_"):
        token = text.split("link_", 1)[-1].strip()
        uid = verify_link_token(token)
        if uid and chat_id:
            link_telegram(uid, chat_id)
            return chat_id, "Connected to Sprout 🌱 — drop me a one-line idea anytime."
        return chat_id, "That link expired — grab a fresh one from the dashboard."

    if not text:
        return chat_id, SCRIPTED_NUDGE
    if text.lower().startswith("/start"):
        return chat_id, "Hey — I'm Sprout 🌱 Connect me from the dashboard, or drop a video idea."

    from .db.context import UserContext, set_current_user
    from sqlmodel import select

    with sync_session() as session:
        user = session.exec(select(User).where(User.telegram_chat_id == chat_id)).first()
    if user:
        set_current_user(UserContext(
            uid=user.uid,
            is_demo=user.is_demo,
            cognee_user_id=user.cognee_user_id,
            cognee_dataset_id=user.cognee_dataset_id,
            telegram_chat_id=chat_id,
        ))
        save_idea(text[:120], state="seed", provenance="telegram", uid=user.uid)
        return chat_id, f'Saved as a seed: "{text[:80]}" — plant it on the board when ready.'

    return chat_id, "Link your Telegram from the Sprout dashboard first."


def _load_offset() -> int:
    with sync_session() as session:
        row = session.get(TelegramPollState, 1)
        return row.offset if row else 0


def _save_offset(offset: int) -> None:
    with sync_session() as session:
        row = session.get(TelegramPollState, 1)
        if not row:
            row = TelegramPollState(id=1, offset=offset)
        else:
            row.offset = offset
        session.add(row)
        session.commit()


def poll_once(timeout: int = 0) -> list[dict]:
    if not TELEGRAM_BOT_TOKEN:
        return []
    offset = _load_offset()
    result = _api("getUpdates", {"offset": offset, "timeout": timeout})
    if not result or not result.get("ok"):
        return []
    processed = []
    for update in result.get("result", []):
        chat_id, reply = handle_update(update)
        if chat_id:
            send_message(reply, chat_id=chat_id)
        processed.append({"update_id": update["update_id"], "chat_id": chat_id, "reply": reply})
        offset = update["update_id"] + 1
    if processed:
        _save_offset(offset)
    return processed


async def poll_forever() -> None:
    while True:
        try:
            await asyncio.to_thread(poll_once, 30)
        except Exception as e:
            print(f"telegram poll_forever: {e}")
            await asyncio.sleep(5)


def get_scripted_nudge() -> str:
    return SCRIPTED_NUDGE

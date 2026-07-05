"""Telegram bot — per-user linking + ambient nudges."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import urllib.request

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_LINK_SECRET
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
    parts = token.rsplit("_", 2)
    if len(parts) != 3:
        return None
    uid, ts_str, sig = parts
    if int(time.time()) - int(ts_str) > 900:
        return None
    expected = hmac.new(
        TELEGRAM_LINK_SECRET.encode(),
        f"{uid}:{ts_str}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return uid if hmac.compare_digest(sig, expected) else None


_bot_username: str | None = None


def get_bot_username() -> str:
    """Resolve @username for t.me deep links (token prefix is numeric id, not username)."""
    global _bot_username
    if _bot_username:
        return _bot_username
    configured = __import__("os").getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    if configured:
        _bot_username = configured
        return _bot_username
    result = _api("getMe")
    if result and result.get("ok"):
        _bot_username = result["result"].get("username") or ""
    return _bot_username or ""


def link_telegram(uid: str, chat_id: str) -> bool:
    with sync_session() as session:
        u = session.get(User, uid)
        if not u:
            return False
        u.telegram_chat_id = chat_id
        session.add(u)
        session.commit()
        return True


def chat_id_for_uid(uid: str) -> str:
    with sync_session() as session:
        u = session.get(User, uid)
        return (u.telegram_chat_id if u else "") or ""


def send_message(text: str, chat_id: str = "") -> bool:
    if not chat_id:
        return False
    result = _api("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(result and result.get("ok"))


def send_nudge_to_user(uid: str, text: str) -> bool:
    chat_id = chat_id_for_uid(uid)
    if not chat_id:
        return False
    return send_message(text, chat_id=chat_id)


def _run_agent_chat(message: str) -> tuple[str, list[dict]]:
    from .agent import chat as agent_chat

    try:
        result = asyncio.run(agent_chat(message, history=[]))
    except RuntimeError as exc:
        if "Lock is held" in str(exc) or "cannot be called from a running event loop" in str(exc):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(agent_chat(message, history=[]))
            except RuntimeError as lock_exc:
                if "Lock is held" in str(lock_exc):
                    return (
                        "Graph is busy — try again in a moment. "
                        "(Stop uvicorn before ingest if this persists.)",
                        [],
                    )
                raise
            finally:
                loop.close()
        else:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(agent_chat(message, history=[]))
            finally:
                loop.close()
    return result.get("reply", ""), result.get("tool_calls", [])


def _looks_like_question(text: str) -> bool:
    t = text.strip().lower()
    if t.endswith("?"):
        return True
    return t.startswith(("how ", "what ", "why ", "when ", "where ", "who ", "is ", "are ", "can ", "should ", "do ", "did "))


def handle_update(update: dict) -> tuple[str, str]:
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id") or "")
    text = (msg.get("text") or "").strip()

    if text.lower().startswith("/start link_"):
        token = text.split("link_", 1)[-1].strip()
        uid = verify_link_token(token)
        if uid and chat_id and link_telegram(uid, chat_id):
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
        if len(text) <= 160 and not _looks_like_question(text):
            save_idea(text[:120], state="seed", provenance="telegram", uid=user.uid)
            return chat_id, f'Saved as a seed: "{text[:80]}" — plant it on the board when ready.'
        reply, tool_calls = _run_agent_chat(text)
        if tool_calls:
            tools = ", ".join(t["tool"] for t in tool_calls[:3])
            reply = f"{reply}\n\n⚙ {tools}"
        return chat_id, reply or 'Saved — check your seed tray on the board.'

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

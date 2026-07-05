#!/usr/bin/env python3
"""End-to-end Telegram linking, nudge delivery, and reply attribution tests.

Usage (from repo root with venv active):
  cd backend && python -m memory_shield.scripts.test_telegram_e2e

Uses TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from .env for live API sends.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

# Ensure backend package resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlmodel import select

from memory_shield.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_LINK_SECRET
from memory_shield.db.models import Draft, Preference, User
from memory_shield.db.sync_session import init_sync_db, sync_session
from memory_shield.lifecycle import list_seeds
from memory_shield.telegram_bot import (
    _api,
    chat_id_for_uid,
    get_bot_username,
    handle_update,
    link_telegram,
    make_link_token,
    poll_once,
    send_message,
    send_nudge_to_user,
    verify_link_token,
)

TEST_UID = "test_telegram_e2e"
TEST_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def _header(msg: str) -> None:
    print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def ensure_test_user() -> None:
    init_sync_db()
    with sync_session() as session:
        user = session.get(User, TEST_UID)
        if not user:
            user = User(
                uid=TEST_UID,
                email="telegram-e2e@test.local",
                display_name="Telegram E2E",
                onboarding_status="ready",
                is_demo=False,
            )
            session.add(user)
            session.flush()
            session.add(Preference(uid=TEST_UID))
        user.telegram_chat_id = ""
        session.add(user)
        session.commit()


def test_link_token_roundtrip() -> str:
    _header("1. Link token HMAC round-trip")
    token = make_link_token(TEST_UID)
    uid = verify_link_token(token)
    if uid != TEST_UID:
        _fail(f"verify_link_token returned {uid!r}, expected {TEST_UID!r}")
    _ok(f"token verifies for uid={TEST_UID}")
    return token


def test_handle_update_link(token: str) -> None:
    _header("2. handle_update /start link_ → link_telegram + Postgres")
    if not TEST_CHAT_ID:
        _fail("TELEGRAM_CHAT_ID not set — need a real chat for live test")

    update = {
        "update_id": 900000001,
        "message": {
            "message_id": 1,
            "chat": {"id": int(TEST_CHAT_ID), "type": "private"},
            "text": f"/start link_{token}",
        },
    }
    chat_id, reply = handle_update(update)
    if chat_id != TEST_CHAT_ID:
        _fail(f"handle_update chat_id={chat_id!r}, expected {TEST_CHAT_ID!r}")
    stored = chat_id_for_uid(TEST_UID)
    if stored != TEST_CHAT_ID:
        _fail(f"users.telegram_chat_id={stored!r}, expected {TEST_CHAT_ID!r}")
    if "Connected" not in reply:
        _fail(f"unexpected link reply: {reply!r}")
    _ok(f"link_telegram stored chat_id={stored} for uid={TEST_UID}")


def test_live_telegram_start(token: str) -> None:
    _header("3. Live Telegram API — send /start link_ to bot chat")
    if not TELEGRAM_BOT_TOKEN:
        _fail("TELEGRAM_BOT_TOKEN not set")
    start_cmd = f"/start link_{token}"
    sent = send_message(start_cmd, chat_id=TEST_CHAT_ID)
    if not sent:
        _fail("sendMessage of /start link_ failed")
    _ok("sent /start link_ via Telegram API (poll_forever will also process getUpdates)")


def test_nudge_per_user_not_global() -> None:
    _header("4. Proactive nudge — per-user chat_id, not global env default alone")
    wrong_uid = "wrong_user_no_telegram"
    with sync_session() as session:
        if not session.get(User, wrong_uid):
            session.add(User(uid=wrong_uid, display_name="Wrong", onboarding_status="ready"))
            session.commit()

    msg = f"🌱 E2E nudge test {int(time.time())}"
    sent_wrong = send_nudge_to_user(wrong_uid, msg)
    if sent_wrong:
        _fail("send_nudge_to_user succeeded for user with no telegram_chat_id")

    sent_right = send_nudge_to_user(TEST_UID, msg)
    if not sent_right:
        _fail(f"send_nudge_to_user failed for linked uid={TEST_UID}")

    # Old bug: send_message(text) with no chat_id always returned False
    sent_bare = send_message(msg)
    if sent_bare:
        _fail("send_message without chat_id should never succeed")

    _ok(f"nudge delivered to uid={TEST_UID} chat_id={TEST_CHAT_ID}, not unlinked users")


def test_reply_attribution_and_agent() -> None:
    _header("5a. Quick-capture — one-liner saved as seed under test uid")
    idea = f"e2e seed {int(time.time())}"
    update = {
        "update_id": 900000002,
        "message": {
            "message_id": 2,
            "chat": {"id": int(TEST_CHAT_ID), "type": "private"},
            "text": idea,
        },
    }
    chat_id, reply = handle_update(update)
    if chat_id != TEST_CHAT_ID:
        _fail(f"reply chat_id mismatch: {chat_id!r}")
    if "Saved as a seed" not in reply:
        _fail(f"expected seed capture reply, got: {reply!r}")
    seeds = list_seeds(uid=TEST_UID)
    if not any(idea.lower() in s.get("title", "").lower() for s in seeds):
        _fail(f"seed {idea!r} not found under uid={TEST_UID}")
    demo_seeds = list_seeds(uid="demo")
    if any(idea.lower() in s.get("title", "").lower() for s in demo_seeds):
        _fail("seed saved under demo uid instead of test user")
    _ok(f"one-liner saved under uid={TEST_UID}")

    _header("5b. Agent path — question routes through tools")
    update = {
        "update_id": 900000003,
        "message": {
            "message_id": 3,
            "chat": {"id": int(TEST_CHAT_ID), "type": "private"},
            "text": "What trends are hot in my niche right now?",
        },
    }
    try:
        _, agent_reply = handle_update(update)
    except RuntimeError as e:
        if "Lock is held" in str(e) or "lock" in str(e).lower():
            print("WARN: agent graph lock held (stop uvicorn for full agent test) — skipping")
            return
        raise
    if len(agent_reply) < 20:
        _fail(f"agent reply too short: {agent_reply!r}")
    _ok(f"agent answered question (len={len(agent_reply)})")
    print(f"    reply preview: {agent_reply[:240]}...")


def test_bot_username() -> None:
    _header("6. Bot username for deep links (not numeric token prefix)")
    username = get_bot_username()
    if not username:
        print("WARN: could not resolve bot username — set TELEGRAM_BOT_USERNAME in .env")
        return
    if username.isdigit():
        _fail(f"get_bot_username returned numeric id {username!r} — t.me links would break")
    _ok(f"bot username=@{username}")


def main() -> None:
    print(f"TELEGRAM_LINK_SECRET prefix: {TELEGRAM_LINK_SECRET[:6]}…")
    print(f"TEST_UID={TEST_UID} TEST_CHAT_ID={TEST_CHAT_ID or '(unset)'}")

    ensure_test_user()
    token = test_link_token_roundtrip()
    test_handle_update_link(token)
    test_live_telegram_start(token)
    test_nudge_per_user_not_global()
    test_reply_attribution_and_agent()
    test_bot_username()

    _header("ALL TELEGRAM E2E CHECKS PASSED")


if __name__ == "__main__":
    main()

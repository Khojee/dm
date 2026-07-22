"""Parser for Telegram Desktop JSON exports (result.json)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .base import Message, load_json

logger = logging.getLogger(__name__)


def _extract_text(raw: Any) -> str:
    """Telegram `text` can be a string or a list of strings/entity dicts."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for chunk in raw:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                parts.append(chunk.get("text", ""))
        return "".join(parts)
    return ""


def _classify_media(msg: dict[str, Any]) -> tuple[str | None, dict[str, bool]]:
    """Determine media type flags for a Telegram message dict."""
    flags = {
        "is_photo": False,
        "is_video": False,
        "is_voice": False,
        "is_sticker": False,
        "is_gif": False,
        "is_file": False,
        "is_share": False,
    }
    media_type = msg.get("media_type")
    if "photo" in msg:
        flags["is_photo"] = True
        return "photo", flags
    if media_type == "sticker":
        flags["is_sticker"] = True
        return "sticker", flags
    if media_type in ("voice_message",):
        flags["is_voice"] = True
        return "voice", flags
    if media_type in ("video_message",):
        flags["is_video"] = True
        return "video_note", flags
    if media_type in ("video_file",):
        flags["is_video"] = True
        return "video", flags
    if media_type in ("animation",):
        flags["is_gif"] = True
        return "gif", flags
    if media_type in ("audio_file",):
        flags["is_file"] = True
        return "file", flags
    if "file" in msg:
        flags["is_file"] = True
        return "file", flags
    return None, flags


def _parse_reactions(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Telegram reactions to [{'emoji', 'actor'}]."""
    out: list[dict[str, Any]] = []
    for reaction in msg.get("reactions", []) or []:
        emoji_char = reaction.get("emoji", "")
        for actor in reaction.get("recent", []) or []:
            out.append({"emoji": emoji_char, "actor": actor.get("from", "")})
        if not reaction.get("recent"):
            out.append({"emoji": emoji_char, "actor": ""})
    return out


def _iter_chat_messages(chat: dict[str, Any]) -> Iterator[Message]:
    """Yield unified messages from a single Telegram chat dict."""
    chat_id = str(chat.get("id", "unknown"))
    chat_name = chat.get("name") or "Telegram Chat"
    for msg in chat.get("messages", []):
        if msg.get("type") != "message":
            continue
        date_str = msg.get("date")
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str)
        except ValueError:
            continue
        sender = msg.get("from") or ""
        media_type, flags = _classify_media(msg)
        yield Message(
            datetime=dt,
            sender=sender,
            text=_extract_text(msg.get("text", "")),
            platform="telegram",
            conversation_id=f"tg_{chat_id}",
            conversation_name=chat_name,
            media_type=media_type,
            is_media=media_type is not None,
            reactions=_parse_reactions(msg),
            duration_seconds=msg.get("duration_seconds"),
            edited="edited" in msg,
            **flags,
        )


def parse_telegram(data_dir: Path) -> list[Message]:
    """Recursively find Telegram exports under `data_dir` and parse all chats.

    Supports both single-chat exports (result.json with `messages` at top
    level) and full exports (`chats.list`).
    """
    messages: list[Message] = []
    json_files = sorted(data_dir.rglob("*.json"))
    for path in json_files:
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        chats: list[dict[str, Any]] = []
        if "messages" in data and isinstance(data["messages"], list):
            chats = [data]
        elif "chats" in data and isinstance(data.get("chats"), dict):
            chats = data["chats"].get("list", [])
        else:
            continue
        for chat in chats:
            parsed = list(_iter_chat_messages(chat))
            messages.extend(parsed)
            logger.info("Telegram: parsed %d messages from '%s' (%s)",
                        len(parsed), chat.get("name"), path.name)
    return messages

"""Parser for Instagram / Threads data exports (message_*.json threads)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import Message, fix_mojibake, load_json

logger = logging.getLogger(__name__)

# Meta placeholder strings that are not real user text
_PLACEHOLDER_PREFIXES = (
    "You sent an attachment",
    "sent an attachment",
    "Liked a message",
    "Reacted",
    "This poll is no longer available",
    "shared a story",
)


def _is_placeholder(text: str) -> bool:
    """True if the content is a Meta-generated placeholder, not user text."""
    low = text.strip()
    return any(low.endswith(sfx) or low.startswith(sfx) for sfx in _PLACEHOLDER_PREFIXES)


def _classify(msg: dict[str, Any]) -> tuple[str | None, dict[str, bool]]:
    """Determine media type flags for an Instagram message dict."""
    flags = {
        "is_photo": False,
        "is_video": False,
        "is_voice": False,
        "is_sticker": False,
        "is_gif": False,
        "is_file": False,
        "is_share": False,
    }
    if msg.get("photos"):
        flags["is_photo"] = True
        return "photo", flags
    if msg.get("videos"):
        flags["is_video"] = True
        return "video", flags
    if msg.get("audio_files"):
        flags["is_voice"] = True
        return "voice", flags
    if msg.get("gifs"):
        flags["is_gif"] = True
        return "gif", flags
    if msg.get("sticker"):
        flags["is_sticker"] = True
        return "sticker", flags
    if msg.get("files"):
        flags["is_file"] = True
        return "file", flags
    if msg.get("share"):
        flags["is_share"] = True
        link = (msg.get("share") or {}).get("link", "") or ""
        if "/reel/" in link:
            return "reel", flags
        if "threads.com" in link or "threads.net" in link:
            return "thread_share", flags
        return "share", flags
    return None, flags


def _parse_reactions(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Instagram reactions to [{'emoji', 'actor'}]."""
    out: list[dict[str, Any]] = []
    for reaction in msg.get("reactions", []) or []:
        out.append({
            "emoji": fix_mojibake(reaction.get("reaction", "")),
            "actor": fix_mojibake(reaction.get("actor", "")),
        })
    return out


def _thread_kind(thread_path: str, share_links: list[str]) -> str:
    """Heuristic: distinguish a Threads-app DM thread from a regular IG DM."""
    threads_hits = sum(1 for l in share_links if "threads.com" in l or "threads.net" in l)
    if share_links and threads_hits / len(share_links) > 0.5:
        return "threads"
    return "instagram"


def parse_instagram(data_dir: Path) -> list[Message]:
    """Recursively find Instagram/Threads message threads and parse them.

    Handles `message_*.json` files under inbox/ and message_requests/, fixes
    Meta's mojibake encoding, and classifies media/share types.
    """
    messages: list[Message] = []
    thread_files: dict[str, list[Path]] = {}
    for path in sorted(data_dir.rglob("message_*.json")):
        thread_files.setdefault(str(path.parent), []).append(path)

    for thread_dir, paths in thread_files.items():
        thread_msgs: list[Message] = []
        title = Path(thread_dir).name
        share_links: list[str] = []
        joinable = False
        for path in paths:
            data = load_json(path)
            if not isinstance(data, dict) or "messages" not in data:
                continue
            joinable = joinable or "joinable_mode" in data
            title = fix_mojibake(data.get("title") or title)
            for msg in data["messages"]:
                ts = msg.get("timestamp_ms")
                if ts is None:
                    continue
                dt = datetime.fromtimestamp(ts / 1000.0)
                sender = fix_mojibake(msg.get("sender_name", ""))
                raw_text = fix_mojibake(msg.get("content", "") or "")
                media_type, flags = _classify(msg)
                if msg.get("share"):
                    link = (msg.get("share") or {}).get("link", "") or ""
                    if link:
                        share_links.append(link)
                text = "" if _is_placeholder(raw_text) else raw_text
                thread_msgs.append(Message(
                    datetime=dt,
                    sender=sender,
                    text=text,
                    platform="instagram",  # refined below
                    conversation_id=f"ig_{Path(thread_dir).name}",
                    conversation_name=title,
                    media_type=media_type,
                    is_media=media_type is not None,
                    reactions=_parse_reactions(msg),
                    **flags,
                ))
        kind = "threads" if joinable else _thread_kind(thread_dir, share_links)
        # A thread is likely a Threads-app conversation if joinable/dominated
        # by threads.com shares; refine platform label per-thread.
        if kind == "threads":
            for m in thread_msgs:
                m.platform = "threads"
        messages.extend(thread_msgs)
        logger.info("Instagram: parsed %d messages from thread '%s' (%s)",
                    len(thread_msgs), title, kind)
    return messages

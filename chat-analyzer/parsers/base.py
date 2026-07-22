"""Shared helpers and the unified message record model used by all parsers."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\u2764\u2665\u2661\ufe0f"
    "]+",
    flags=re.UNICODE,
)


@dataclass
class Message:
    """A single unified chat message across platforms."""

    datetime: datetime
    sender: str
    text: str
    platform: str
    conversation_id: str
    conversation_name: str
    media_type: Optional[str] = None  # photo|video|voice|sticker|gif|file|share|video_note
    is_media: bool = False
    is_voice: bool = False
    is_photo: bool = False
    is_video: bool = False
    is_sticker: bool = False
    is_gif: bool = False
    is_share: bool = False
    is_file: bool = False
    reactions: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: Optional[float] = None
    edited: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for DataFrame construction."""
        return asdict(self)


def fix_mojibake(text: str) -> str:
    """Repair Meta's latin-1 encoded UTF-8 strings (e.g. 'ð' -> emoji)."""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def extract_emojis(text: str) -> list[str]:
    """Extract individual emoji characters from a string."""
    try:
        import emoji as emoji_lib

        return [m["emoji"] for m in emoji_lib.emoji_list(text)]
    except ImportError:  # pragma: no cover - fallback
        return EMOJI_PATTERN.findall(text)


def load_json(path: Path) -> Any:
    """Load a JSON file with UTF-8 encoding, logging failures."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def name_matches(name: str, aliases: Iterable[str]) -> bool:
    """Case-insensitive alias match."""
    low = (name or "").strip().lower()
    return any(low == a.strip().lower() for a in aliases)

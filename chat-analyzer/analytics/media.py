"""Media analytics: photos, videos, voice notes, stickers, shares, reels."""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_media(df: pd.DataFrame) -> dict[str, Any]:
    """Count media by type, sender and over time."""
    media = df[df["is_media"]]

    by_type = {t: int(c) for t, c in media.groupby("media_type").size().items()}
    by_type_sender = {
        f"{t}|{s}": int(c)
        for (t, s), c in media.groupby(["media_type", "sender"]).size().items()
    }
    monthly = {
        m: int(c) for m, c in media.groupby("month").size().items()
    }

    voice = df[df["is_voice"]]
    voice_seconds = float(voice["duration_seconds"].fillna(0).sum())

    return {
        "total_media": int(len(media)),
        "by_type": by_type,
        "by_type_sender": by_type_sender,
        "by_sender": {s: int(c) for s, c in media.groupby("sender").size().items()},
        "monthly": sorted(monthly.items()),
        "voice_total_seconds": voice_seconds,
        "photos": int(df["is_photo"].sum()),
        "videos": int(df["is_video"].sum()),
        "voice_notes": int(df["is_voice"].sum()),
        "stickers": int(df["is_sticker"].sum()),
        "gifs": int(df["is_gif"].sum()),
        "files": int(df["is_file"].sum()),
        "shares": int(df["is_share"].sum()),
        "reels": by_type.get("reel", 0),
    }

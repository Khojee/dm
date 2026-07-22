"""Fun awards computed from real statistics — no fabrication."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _winner(scores: dict[str, float], higher_wins: bool = True) -> str | None:
    """Return the key with max (or min) score, None on empty/tie-at-zero."""
    if not scores:
        return None
    items = sorted(scores.items(), key=lambda x: x[1], reverse=higher_wins)
    if items[0][1] == 0:
        return None
    return items[0][0]


def compute_awards(df: pd.DataFrame, conv: dict[str, Any],
                   emoji_stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the award list. Each award includes the evidence used."""
    awards: list[dict[str, Any]] = []
    senders = sorted(df["sender"].unique())

    def add(icon: str, title: str, winner: str | None, evidence: str) -> None:
        if winner:
            awards.append({"icon": icon, "title": title, "winner": winner,
                           "evidence": evidence})

    # Night Owl: share of messages 22:00–05:00
    night = df[(df["hour"] >= 22) | (df["hour"] < 5)]
    night_scores = {s: len(night[night["sender"] == s]) / max(len(df[df["sender"] == s]), 1)
                    for s in senders}
    w = _winner(night_scores)
    if w:
        add("🦉", "Night Owl", w, f"{night_scores[w]*100:.0f}% of their messages sent after 10pm")

    # Early Bird: 5:00–9:00
    early = df[(df["hour"] >= 5) & (df["hour"] < 9)]
    early_scores = {s: len(early[early["sender"] == s]) / max(len(df[df["sender"] == s]), 1)
                    for s in senders}
    w = _winner(early_scores)
    if w:
        add("🌅", "Early Bird", w, f"{early_scores[w]*100:.0f}% of their messages before 9am")

    # Essay Writer: avg words per text message
    texty = df[df["word_count"] > 0]
    essay = {s: float(g["word_count"].mean()) for s, g in texty.groupby("sender")}
    w = _winner(essay)
    if w:
        add("📜", "Essay Writer", w, f"averages {essay[w]:.1f} words per message")

    # Fast Responder: lowest median reply time
    resp = conv.get("response", {})
    speed = {s: v["median_s"] for s, v in resp.items()}
    if speed:
        w = min(speed, key=speed.get)
        add("⚡", "Lightning Replier", w, f"median reply time {resp[w]['median_h']}")

    # Ghost: highest median reply time
    if len(speed) >= 2:
        w = max(speed, key=speed.get)
        add("👻", "Professional Ghost", w, f"median reply time {resp[w]['median_h']}")

    # Emoji Master
    ec = emoji_stats.get("emoji_count_by_sender", {})
    w = _winner({s: float(v) for s, v in ec.items()})
    if w:
        add("🎭", "Emoji Master", w, f"used {ec[w]} emojis in total")

    # Reaction King/Queen
    ra = emoji_stats.get("reactions_by_actor", {})
    w = _winner({s: float(v) for s, v in ra.items()})
    if w:
        add("💖", "Reaction Royalty", w, f"gave {ra[w]} reactions")

    # Meme Machine: shares + gifs + reels
    memes = df[df["media_type"].isin(["share", "reel", "gif", "thread_share"])]
    meme_scores = {s: float(c) for s, c in memes.groupby("sender").size().items()}
    w = _winner(meme_scores)
    if w:
        add("🤡", "Meme Machine", w, f"shared {int(meme_scores[w])} links, reels & gifs")

    # Voice Note Lover
    voice = df[df["is_voice"]]
    v_scores = {s: float(c) for s, c in voice.groupby("sender").size().items()}
    w = _winner(v_scores)
    if w:
        add("🎙️", "Voice Note Lover", w, f"sent {int(v_scores[w])} voice messages")

    # Photographer
    photos = df[df["is_photo"]]
    p_scores = {s: float(c) for s, c in photos.groupby("sender").size().items()}
    w = _winner(p_scores)
    if w:
        add("📷", "Resident Photographer", w, f"sent {int(p_scores[w])} photos")

    # Conversation Starter
    starters = conv.get("conversation_starters", {})
    w = _winner({s: float(v) for s, v in starters.items()})
    if w:
        add("🚀", "Conversation Igniter", w, f"started {starters[w]} conversations")

    # Conversation Saver: broke the longest silences (initiated after >1d gaps)
    gaps = df["datetime"].diff().dt.total_seconds()
    revivals = df[gaps > 86400]
    r_scores = {s: float(c) for s, c in revivals.groupby("sender").size().items()}
    w = _winner(r_scores)
    if w:
        add("🛟", "Silence Breaker", w, f"revived the chat {int(r_scores[w])} times after 1+ day gaps")

    # Double Texter
    dt_scores = {s: float(v) for s, v in conv.get("double_texting", {}).items()}
    w = _winner(dt_scores)
    if w:
        add("📱", "Double-Text Champion", w, f"{int(dt_scores[w])} follow-up texts without a reply")

    # Chatterbox: most messages overall
    counts = {s: float(c) for s, c in df.groupby("sender").size().items()}
    w = _winner(counts)
    if w:
        add("💬", "The Chatterbox", w, f"sent {int(counts[w])} messages "
            f"({counts[w]/len(df)*100:.0f}% of the chat)")

    return awards

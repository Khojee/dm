"""Milestone detection: firsts, message-count landmarks, records."""

from __future__ import annotations

from typing import Any

import pandas as pd

HEART_CHARS = set("❤❤️🧡💛💚💙💜🖤🤍💕💞💓💗💖💘💝🥰😍")


def _event(dt: pd.Timestamp, title: str, detail: str, icon: str) -> dict[str, Any]:
    return {"date": str(dt.date()), "datetime": str(dt), "title": title,
            "detail": detail, "icon": icon}


def compute_timeline(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Detect notable milestones in chronological order."""
    events: list[dict[str, Any]] = []
    first = df.iloc[0]
    events.append(_event(
        first["datetime"], "First message ever",
        f"{first['sender']} on {first['platform'].title()}"
        + (f': "{first["text"][:80]}"' if first["text"] else " (media)"),
        "🌱"))

    # First message per platform
    for platform, g in df.groupby("platform"):
        row = g.iloc[0]
        if row.name != first.name:
            events.append(_event(
                row["datetime"], f"First {platform.title()} message",
                f"{row['sender']}" + (f': "{row["text"][:80]}"' if row["text"] else ""),
                {"telegram": "✈️", "instagram": "📸", "threads": "🧵"}.get(platform, "💬")))

    # Count landmarks
    for n in [100, 500, 1000, 2500, 5000, 10000]:
        if len(df) >= n:
            row = df.iloc[n - 1]
            events.append(_event(row["datetime"], f"{n:,}th message",
                                 f"Sent by {row['sender']}", "🎯"))

    # First heart emoji (text or reaction)
    heart_time, heart_by, heart_how = None, None, None
    for _, row in df.iterrows():
        if any(any(h in e for h in HEART_CHARS) for e in row["emoji_list"]):
            heart_time, heart_by, heart_how = row["datetime"], row["sender"], "in a message"
            break
        if any(any(h in (r.get("emoji") or "") for h in HEART_CHARS) for r in row["reactions"] or []):
            actor = next((r["actor"] for r in row["reactions"] if any(h in (r.get("emoji") or "") for h in HEART_CHARS)), "")
            heart_time, heart_by, heart_how = row["datetime"], actor, "as a reaction"
            break
    if heart_time is not None:
        events.append(_event(heart_time, "First heart", f"From {heart_by} {heart_how}", "❤️"))

    # First media of each kind
    for flag, label, icon in [("is_photo", "First photo", "🖼️"),
                              ("is_voice", "First voice message", "🎙️"),
                              ("is_video", "First video", "🎬"),
                              ("is_sticker", "First sticker", "🩵")]:
        sub = df[df[flag]]
        if len(sub):
            row = sub.iloc[0]
            events.append(_event(row["datetime"], label, f"Sent by {row['sender']}", icon))

    # Longest conversation session
    counts = df.groupby("session_id").size()
    big = counts.idxmax()
    sess = df[df["session_id"] == big]
    dur = (sess["datetime"].max() - sess["datetime"].min()).total_seconds() / 60
    events.append(_event(sess["datetime"].iloc[0], "Longest conversation",
                         f"{int(counts.max())} messages over {dur:.0f} minutes", "🔥"))

    # Longest reply gap
    gaps = df["datetime"].diff().dt.total_seconds()
    gi = gaps.idxmax()
    days = gaps.max() / 86400
    events.append(_event(df.loc[gi, "datetime"], "Longest silence broken",
                         f"{days:.1f} days of silence, broken by {df.loc[gi, 'sender']}", "🕊️"))

    # Most active week
    weekly = df.set_index("datetime").resample("W").size()
    wk = weekly.idxmax()
    events.append(_event(wk, "Most active week",
                         f"{int(weekly.max())} messages in one week", "📈"))

    events.sort(key=lambda e: e["datetime"])
    return events

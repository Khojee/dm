"""Spotify-Wrapped-style yearly recap and monthly summaries."""

from __future__ import annotations

from typing import Any

import pandas as pd

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def compute_recap(df: pd.DataFrame) -> list[dict[str, Any]]:
    """One wrapped card per calendar year."""
    recaps: list[dict[str, Any]] = []
    for year, g in df.groupby("year"):
        from collections import Counter
        emojis: Counter[str] = Counter()
        for lst in g["emoji_list"]:
            emojis.update(lst)
        daily = g.groupby("date").size()
        busiest_date = daily.idxmax()
        hours = g.groupby("hour").size()
        recaps.append({
            "year": int(year),
            "messages": int(len(g)),
            "words": int(g["word_count"].sum()),
            "active_days": int(daily.count()),
            "by_sender": {s: int(c) for s, c in g.groupby("sender").size().items()},
            "top_emoji": emojis.most_common(1)[0][0] if emojis else None,
            "top_emojis": [e for e, _ in emojis.most_common(5)],
            "busiest_day": {"date": str(busiest_date), "count": int(daily.max())},
            "favorite_hour": int(hours.idxmax()),
            "media_sent": int(g["is_media"].sum()),
            "platforms": {p: int(c) for p, c in g.groupby("platform").size().items()},
        })
    return recaps


def compute_monthly_summaries(df: pd.DataFrame) -> list[dict[str, Any]]:
    """A compact factual summary per month."""
    out: list[dict[str, Any]] = []
    for month, g in df.groupby("month"):
        from collections import Counter
        emojis: Counter[str] = Counter()
        for lst in g["emoji_list"]:
            emojis.update(lst)
        replies = g[g["reply_time"].notna() & (g["reply_time"] < 6 * 3600)]
        y, m = month.split("-")
        out.append({
            "month": month,
            "label": f"{MONTH_NAMES[int(m)-1]} {y}",
            "messages": int(len(g)),
            "words": int(g["word_count"].sum()),
            "by_sender": {s: int(c) for s, c in g.groupby("sender").size().items()},
            "top_emoji": emojis.most_common(1)[0][0] if emojis else None,
            "media": int(g["is_media"].sum()),
            "median_reply_s": float(replies["reply_time"].median()) if len(replies) else None,
            "active_days": int(g["date"].nunique()),
        })
    return out

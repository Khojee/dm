"""Conversation dynamics: response times, starters/enders, double texting, silences."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _fmt_seconds(s: float) -> str:
    """Human readable duration."""
    s = float(s)
    if s < 60:
        return f"{int(s)}s"
    if s < 3600:
        return f"{int(s // 60)}m {int(s % 60)}s"
    if s < 86400:
        return f"{int(s // 3600)}h {int((s % 3600) // 60)}m"
    return f"{int(s // 86400)}d {int((s % 86400) // 3600)}h"


def compute_conversation(df: pd.DataFrame) -> dict[str, Any]:
    """Compute response-time stats and session-level conversation dynamics."""
    senders = sorted(df["sender"].unique())

    # Response times (sender changed) — cap at 6h to exclude "new conversation" gaps.
    replies = df[df["reply_time"].notna() & (df["reply_time"] < 6 * 3600)]
    response: dict[str, Any] = {}
    for sender in senders:
        r = replies[replies["sender"] == sender]["reply_time"]
        if len(r) == 0:
            continue
        response[sender] = {
            "median_s": float(r.median()),
            "mean_s": float(r.mean()),
            "median_h": _fmt_seconds(r.median()),
            "fastest_s": float(r.min()),
            "count": int(len(r)),
        }

    # Reply time distribution buckets
    buckets = [(0, 30, "<30s"), (30, 120, "30s–2m"), (120, 600, "2–10m"),
               (600, 3600, "10m–1h"), (3600, 6 * 3600, "1–6h")]
    dist = {}
    for sender in senders:
        r = replies[replies["sender"] == sender]["reply_time"]
        dist[sender] = [int(((r >= lo) & (r < hi)).sum()) for lo, hi, _ in buckets]
    dist_labels = [b[2] for b in buckets]

    fastest = replies.nsmallest(1, "reply_time")
    slowest_all = df[df["reply_time"].notna()]
    slowest = slowest_all.nlargest(1, "reply_time")

    # Session-level stats
    sessions = df.groupby("session_id").agg(
        start=("datetime", "min"),
        end=("datetime", "max"),
        count=("datetime", "size"),
        starter=("sender", "first"),
        ender=("sender", "last"),
    )
    sessions["duration_min"] = (sessions["end"] - sessions["start"]).dt.total_seconds() / 60
    real_sessions = sessions[sessions["count"] >= 3]

    starters = real_sessions["starter"].value_counts().to_dict()
    enders = real_sessions["ender"].value_counts().to_dict()

    longest_sess = sessions.loc[sessions["count"].idxmax()]

    # Longest silence between consecutive messages
    gaps = df["datetime"].diff().dt.total_seconds()
    gi = gaps.idxmax()
    longest_silence = {
        "seconds": float(gaps.max()),
        "human": _fmt_seconds(gaps.max()),
        "from": str(df.loc[gi - 1, "datetime"]) if gi and gi > 0 else None,
        "to": str(df.loc[gi, "datetime"]),
        "broken_by": df.loc[gi, "sender"],
    }

    # Double texting: consecutive messages by same sender with >5 min gap.
    same = df["sender"] == df["sender"].shift()
    double = df[same & (gaps > 300)]
    double_texts = {s: int(c) for s, c in double.groupby("sender").size().items()}

    return {
        "response": response,
        "reply_dist": {"labels": dist_labels, "by_sender": dist},
        "fastest_reply": {
            "sender": fastest.iloc[0]["sender"],
            "seconds": float(fastest.iloc[0]["reply_time"]),
            "human": _fmt_seconds(fastest.iloc[0]["reply_time"]),
        } if len(fastest) else None,
        "slowest_reply": {
            "sender": slowest.iloc[0]["sender"],
            "seconds": float(slowest.iloc[0]["reply_time"]),
            "human": _fmt_seconds(slowest.iloc[0]["reply_time"]),
        } if len(slowest) else None,
        "conversation_starters": {str(k): int(v) for k, v in starters.items()},
        "conversation_enders": {str(k): int(v) for k, v in enders.items()},
        "total_sessions": int(len(real_sessions)),
        "avg_session_minutes": round(float(real_sessions["duration_min"].mean()), 1) if len(real_sessions) else 0,
        "avg_session_messages": round(float(real_sessions["count"].mean()), 1) if len(real_sessions) else 0,
        "longest_session": {
            "date": str(longest_sess["start"].date()),
            "messages": int(longest_sess["count"]),
            "duration_min": round(float(longest_sess["duration_min"]), 1),
            "human": _fmt_seconds(float(longest_sess["duration_min"]) * 60),
        },
        "longest_silence": longest_silence,
        "double_texting": double_texts,
    }

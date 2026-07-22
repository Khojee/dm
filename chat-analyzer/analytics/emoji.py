"""Emoji analytics: top emojis, per-sender favourites, evolution, reactions."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def compute_emoji(df: pd.DataFrame) -> dict[str, Any]:
    """Compute emoji usage stats from text and reactions."""
    all_emojis: Counter[str] = Counter()
    by_sender: dict[str, Counter[str]] = {}
    monthly: dict[str, Counter[str]] = {}

    for _, row in df.iterrows():
        emojis = row["emoji_list"]
        if not emojis:
            continue
        all_emojis.update(emojis)
        by_sender.setdefault(row["sender"], Counter()).update(emojis)
        monthly.setdefault(row["month"], Counter()).update(emojis)

    # Reactions
    reaction_counts: Counter[str] = Counter()
    reactions_by_actor: dict[str, int] = {}
    for _, row in df.iterrows():
        for r in row["reactions"] or []:
            if r.get("emoji"):
                reaction_counts[r["emoji"]] += 1
            actor = r.get("actor", "")
            if actor:
                reactions_by_actor[actor] = reactions_by_actor.get(actor, 0) + 1

    total_msgs = max(len(df), 1)
    msgs_with_emoji = int((df["emoji_count"] > 0).sum())

    top10 = [e for e, _ in all_emojis.most_common(6)]
    evolution = {
        e: [[m, monthly[m].get(e, 0)] for m in sorted(monthly)]
        for e in top10
    }

    return {
        "total_emojis": int(sum(all_emojis.values())),
        "unique_emojis": len(all_emojis),
        "messages_with_emoji_pct": round(msgs_with_emoji / total_msgs * 100, 1),
        "avg_emojis_per_message": round(sum(all_emojis.values()) / total_msgs, 2),
        "top": all_emojis.most_common(20),
        "by_sender": {s: c.most_common(10) for s, c in by_sender.items()},
        "emoji_count_by_sender": {s: int(sum(c.values())) for s, c in by_sender.items()},
        "evolution": evolution,
        "reactions_top": reaction_counts.most_common(10),
        "reactions_by_actor": reactions_by_actor,
        "total_reactions": int(sum(reaction_counts.values())),
    }

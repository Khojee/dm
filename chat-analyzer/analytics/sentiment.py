"""Lightweight lexicon + emoji based sentiment over time.

We avoid heavyweight ML models; the score combines a small multilingual
positive/negative word lexicon with emoji valence, which is honest for
informal, emoji-heavy chats.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

POSITIVE_WORDS = set("""
love like happy great good nice amazing awesome beautiful best cute sweet fun
funny lol haha thanks thank glad wonderful perfect cool wow yay excited enjoy
rahmat zo'r yaxshi ajoyib chiroyli zor juda gozal go'zal
спасибо круто классно отлично хорошо люблю нравится смешно
""".split())

NEGATIVE_WORDS = set("""
sad bad hate angry annoying terrible awful worst cry sorry miss lonely tired
sick hurt pain problem stress worried afraid scared upset
yomon xafa charchadim kasal muammo qiyin
плохо грустно устал болит проблема сложно жаль
""".split())

POSITIVE_EMOJI = set("😀😃😄😁😆😂🤣😊😍🥰😘😗☺️😚🤗🤩😋😜🤪❤️❤🧡💛💚💙💜🖤🤍💕💞💓💗💖💘💝✨🎉🥳👍🙌🔥💪😻🤝🙂")
NEGATIVE_EMOJI = set("😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬💔😰😨😱😥😓🙄😒👎")


def _score_row(text: str, emojis: list[str]) -> float:
    """Score in [-1, 1]; 0 for neutral/unscorable."""
    score = 0.0
    hits = 0
    for w in text.lower().split():
        w = w.strip(".,!?…:;()\"'")
        if w in POSITIVE_WORDS:
            score += 1
            hits += 1
        elif w in NEGATIVE_WORDS:
            score -= 1
            hits += 1
    for e in emojis:
        base = e[0] if e else ""
        if e in POSITIVE_EMOJI or base in POSITIVE_EMOJI:
            score += 1
            hits += 1
        elif e in NEGATIVE_EMOJI or base in NEGATIVE_EMOJI:
            score -= 1
            hits += 1
    return score / hits if hits else 0.0


def compute_sentiment(df: pd.DataFrame) -> dict[str, Any]:
    """Weekly sentiment trend and per-sender positivity."""
    scored = df.copy()
    scored["sent"] = [
        _score_row(t, e) for t, e in zip(scored["text"], scored["emoji_list"])
    ]
    nonzero = scored[scored["sent"] != 0]

    weekly = nonzero.set_index("datetime")["sent"].resample("W").mean().dropna()
    monthly = nonzero.groupby("month")["sent"].mean()

    by_sender = {
        s: round(float(g["sent"].mean()), 3)
        for s, g in nonzero.groupby("sender")
    }
    pos_pct = round(float((nonzero["sent"] > 0).mean() * 100), 1) if len(nonzero) else 0

    return {
        "weekly": [[str(d.date()), round(float(v), 3)] for d, v in weekly.items()],
        "monthly": [[m, round(float(v), 3)] for m, v in monthly.items()],
        "by_sender": by_sender,
        "positive_pct": pos_pct,
        "scored_messages": int(len(nonzero)),
    }

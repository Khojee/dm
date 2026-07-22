"""Template-based narrative insights derived strictly from computed stats.

Every sentence is generated from real numbers — nothing is invented.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_insights(df: pd.DataFrame, stats: dict[str, Any]) -> list[dict[str, str]]:
    """Produce human-readable, fact-based observations."""
    insights: list[dict[str, str]] = []
    act = stats["activity"]
    conv = stats["conversation"]
    emo = stats["emoji"]
    words = stats["words"]

    def add(icon: str, title: str, text: str) -> None:
        insights.append({"icon": icon, "title": title, "text": text})

    senders = sorted(df["sender"].unique())

    # Volume balance
    counts = act["by_sender"]
    if len(counts) == 2:
        (s1, c1), (s2, c2) = sorted(counts.items(), key=lambda x: -x[1])
        ratio = c1 / max(c2, 1)
        if ratio < 1.15:
            add("⚖️", "Perfectly balanced",
                f"{s1} sent {c1} messages and {s2} sent {c2} — a nearly equal "
                f"split ({c1/(c1+c2)*100:.0f}% vs {c2/(c1+c2)*100:.0f}%). This conversation is a two-way street.")
        else:
            add("📊", "Who talks more?",
                f"{s1} carries {c1/(c1+c2)*100:.0f}% of the conversation with {c1} messages "
                f"vs {s2}'s {c2}. That's {ratio:.1f}× more.")

    # Platform migration
    plat = act["by_platform"]
    if len(plat) > 1:
        parts = ", ".join(f"{v} on {k.title()}" for k, v in sorted(plat.items(), key=lambda x: -x[1]))
        first_plat = df.iloc[0]["platform"].title()
        last_plat = df.iloc[-1]["platform"].title()
        migration = (f" The story began on {first_plat} and the latest messages are on {last_plat}."
                     if first_plat != last_plat else "")
        add("🌐", "A multi-platform friendship",
            f"You talk across {len(plat)} platforms: {parts}.{migration}")

    # Tempo / trend using first vs second half of the active period
    daily = pd.DataFrame(act["daily"], columns=["date", "n"])
    if len(daily) >= 14:
        half = len(daily) // 2
        first_avg = daily["n"][:half].mean()
        second_avg = daily["n"][half:].mean()
        if second_avg > first_avg * 1.3:
            add("📈", "Getting closer",
                f"Message volume grew from {first_avg:.1f}/day in the first half of the period "
                f"to {second_avg:.1f}/day in the second half — the conversation is accelerating.")
        elif first_avg > second_avg * 1.3:
            add("🍂", "A calmer rhythm",
                f"Message volume moved from {first_avg:.1f}/day early on to "
                f"{second_avg:.1f}/day more recently.")

    # Response style
    resp = conv.get("response", {})
    if len(resp) == 2:
        s_fast = min(resp, key=lambda s: resp[s]["median_s"])
        s_slow = max(resp, key=lambda s: resp[s]["median_s"])
        if s_fast != s_slow:
            add("⏱️", "Reply styles",
                f"{s_fast} typically replies in {resp[s_fast]['median_h']}, while "
                f"{s_slow} takes {resp[s_slow]['median_h']} — different tempos, same conversation.")

    # Message length styles
    lens = words.get("avg_message_length_words", {})
    if len(lens) == 2:
        (l1, v1), (l2, v2) = sorted(lens.items(), key=lambda x: -x[1])
        if v1 > v2 * 1.4:
            add("✍️", "Two writing styles",
                f"{l1} writes longer messages ({v1} words on average) while {l2} keeps it "
                f"snappy ({v2} words). Storyteller meets rapid-fire texter.")

    # Emoji personality
    by_sender_emoji = emo.get("by_sender", {})
    for s in senders:
        top = by_sender_emoji.get(s)
        if top:
            add("😊", f"{s}'s signature emoji",
                f"{s}'s most used emoji is {top[0][0]} ({top[0][1]} times)"
                + (f", followed by {top[1][0]}" if len(top) > 1 else "") + ".")

    # Night pattern
    owl = act.get("night_owl_score", {})
    if owl:
        s = max(owl, key=owl.get)
        if owl[s] >= 15:
            add("🌙", "After-midnight energy",
                f"{owl[s]:.0f}% of {s}'s messages are sent between 10pm and 5am. "
                f"The busiest hour overall is {act['busiest_hour']}:00.")

    # Starters
    starters = conv.get("conversation_starters", {})
    if len(starters) == 2:
        (s1, c1), (s2, c2) = sorted(starters.items(), key=lambda x: -x[1])
        if c1 > c2 * 1.5:
            add("🚪", "Who knocks first",
                f"{s1} starts most conversations ({c1} vs {c2}) — the designated icebreaker.")
        else:
            add("🤝", "Shared initiative",
                f"Conversation starting is shared: {s1} opened {c1} sessions, {s2} opened {c2}.")

    # Peak day
    busiest = act.get("busiest_day", {})
    if busiest:
        add("🏔️", "The biggest day",
            f"On {busiest['date']} you exchanged {busiest['count']} messages — "
            f"the single most active day on record.")

    # Language mix
    langs = words.get("languages", {})
    if len(langs) >= 2:
        names = {"en": "English", "uz": "Uzbek", "ru": "Russian", "tr": "Turkish",
                 "az": "Azerbaijani", "de": "German", "id": "Indonesian",
                 "so": "Somali", "et": "Estonian", "fi": "Finnish", "tl": "Tagalog",
                 "ca": "Catalan", "cy": "Welsh", "sw": "Swahili", "hr": "Croatian",
                 "pl": "Polish", "nl": "Dutch", "fr": "French", "es": "Spanish", "it": "Italian"}
        top_langs = sorted(langs.items(), key=lambda x: -x[1])[:3]
        pretty = ", ".join(f"{names.get(k, k)} ({v})" for k, v in top_langs)
        add("🗣️", "A multilingual chat",
            f"Language detection over longer messages found a mix: {pretty}.")

    return insights

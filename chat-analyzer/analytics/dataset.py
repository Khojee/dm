"""Build the unified pandas DataFrame from parsed messages."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from parsers.base import Message, extract_emojis, name_matches

logger = logging.getLogger(__name__)


def build_dataframe(messages: list[Message], config: dict[str, Any]) -> pd.DataFrame:
    """Convert parsed messages into the unified, enriched DataFrame.

    Normalizes sender names via config aliases, filters to the two
    participants, and derives emoji_list, word_count, reply_time (seconds,
    only when the sender changes), session ids and calendar fields.
    """
    if not messages:
        raise ValueError("No messages parsed from any platform.")

    df = pd.DataFrame([m.to_dict() for m in messages])
    df["datetime"] = pd.to_datetime(df["datetime"])

    me = config["participants"]["me"]
    friend = config["participants"]["friend"]

    def normalize(sender: str) -> str | None:
        if name_matches(sender, me["aliases"]):
            return me["display"]
        if name_matches(sender, friend["aliases"]):
            return friend["display"]
        return None

    # Drop group conversations: any thread containing an outside sender.
    raw_norm = df["sender"].map(normalize)
    bad_convs = df.loc[raw_norm.isna(), "conversation_id"].unique()
    if len(bad_convs):
        logger.info("Dropping %d group/other conversations: %s",
                    len(bad_convs), list(bad_convs))
        df = df[~df["conversation_id"].isin(bad_convs)].copy()

    df["sender"] = df["sender"].map(normalize)
    df["reactions"] = df["reactions"].map(
        lambda rs: [
            {**r, "actor": normalize(r.get("actor", "")) or r.get("actor", "")}
            for r in (rs or [])
        ]
    )
    before = len(df)
    df = df.dropna(subset=["sender"]).copy()
    logger.info("Kept %d/%d messages from the two participants.", len(df), before)

    # Keep only conversations where both participants appear (private DMs).
    conv_ok = df.groupby("conversation_id")["sender"].nunique()
    keep = conv_ok[conv_ok >= 1].index
    df = df[df["conversation_id"].isin(keep)].copy()

    df = df.sort_values("datetime").reset_index(drop=True)

    df["text"] = df["text"].fillna("")
    df["emoji_list"] = df["text"].map(extract_emojis)
    df["emoji_count"] = df["emoji_list"].str.len()
    df["word_count"] = df["text"].str.split().str.len().fillna(0).astype(int)
    df["char_count"] = df["text"].str.len()

    # Reply time: seconds since previous message when sender changed.
    prev_sender = df["sender"].shift()
    prev_time = df["datetime"].shift()
    delta = (df["datetime"] - prev_time).dt.total_seconds()
    df["reply_time"] = delta.where(df["sender"] != prev_sender)

    # Sessions: a new conversation session starts after `session_gap_minutes`.
    gap_s = config.get("session_gap_minutes", 30) * 60
    new_session = delta.isna() | (delta > gap_s)
    df["session_id"] = new_session.cumsum()

    # Calendar helpers
    df["date"] = df["datetime"].dt.date
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.to_period("M").astype(str)
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.dayofweek

    return df

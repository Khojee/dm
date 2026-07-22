"""Build the encrypted chat-analytics dashboard.

Usage:
    python main.py

Reads exports under ``data_dir`` (see config.json), computes all statistics,
encrypts the payload with AES-256-GCM and writes a static site to ``output/``.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from parsers import parse_telegram, parse_instagram
from analytics.dataset import build_dataframe
from analytics.activity import compute_activity
from analytics.response_time import compute_conversation
from analytics.emoji import compute_emoji
from analytics.words import compute_words
from analytics.media import compute_media
from analytics.sentiment import compute_sentiment
from analytics.timeline import compute_timeline
from analytics.awards import compute_awards
from analytics.insights import compute_insights
from analytics.recap import compute_recap, compute_monthly_summaries
from crypto_util import encrypt_payload

ROOT = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s %(name)s — %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("build")


def load_config() -> dict[str, Any]:
    """Load config.json from the project root."""
    with open(ROOT / "config.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def compute_messages_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Basic message-shape statistics."""
    texty = df[df["word_count"] > 0]
    monthly = df.groupby("month").size()
    return {
        "avg_length_words": round(float(texty["word_count"].mean()), 1) if len(texty) else 0,
        "avg_length_chars": round(float(texty["char_count"].mean()), 1) if len(texty) else 0,
        "most_active_month": {"month": str(monthly.idxmax()), "count": int(monthly.max())},
        "text_messages": int(len(texty)),
    }


def build_stats(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Run every analytics module and assemble the payload."""
    logger.info("Computing analytics over %d messages…", len(df))
    stats: dict[str, Any] = {
        "meta": {
            "me": config["participants"]["me"]["display"],
            "friend": config["participants"]["friend"]["display"],
            "generated_days": int((df["datetime"].max() - df["datetime"].min()).days + 1),
        },
        "activity": compute_activity(df),
        "conversation": compute_conversation(df),
        "emoji": compute_emoji(df),
        "words": compute_words(df),
        "media": compute_media(df),
        "sentiment": compute_sentiment(df),
        "messages": compute_messages_stats(df),
        "timeline": compute_timeline(df),
        "recap": compute_recap(df),
        "monthly_summaries": compute_monthly_summaries(df),
    }
    stats["awards"] = compute_awards(df, stats["conversation"], stats["emoji"])
    stats["insights"] = compute_insights(df, stats)
    return stats


def export_site(stats: dict[str, Any], config: dict[str, Any]) -> Path:
    """Encrypt the payload and copy dashboard files into output/."""
    out_dir = ROOT / config.get("output_dir", "output")
    assets_dir = out_dir / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    encrypted = encrypt_payload(stats, config["passphrase"])
    payload_js = "window.__ENCRYPTED_PAYLOAD__ = " + json.dumps(encrypted) + ";"
    (assets_dir / "payload.js").write_text(payload_js, encoding="utf-8")
    logger.info("Encrypted payload: %.1f KB", len(payload_js) / 1024)

    dash = ROOT / "dashboard"
    shutil.copy(dash / "index.html", out_dir / "index.html")
    for name in ("app.js", "charts.js", "style.css"):
        shutil.copy(dash / name, assets_dir / name)
    # Copy any extra static assets
    extra = ROOT / "assets"
    if extra.exists():
        for f in extra.iterdir():
            if f.is_file():
                shutil.copy(f, assets_dir / f.name)
    return out_dir


def main() -> int:
    """Entry point: parse → analyze → encrypt → export."""
    config = load_config()
    data_dir = (ROOT / config["data_dir"]).resolve()
    if not data_dir.exists():
        logger.error("Data directory not found: %s", data_dir)
        return 1

    logger.info("Scanning %s …", data_dir)
    messages = []
    tg_dir = data_dir / "telegram"
    ig_dir = data_dir / "instagram"
    messages += parse_telegram(tg_dir if tg_dir.exists() else data_dir)
    messages += parse_instagram(ig_dir if ig_dir.exists() else data_dir)
    logger.info("Parsed %d raw messages.", len(messages))

    try:
        df = build_dataframe(messages, config)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    stats = build_stats(df, config)
    out_dir = export_site(stats, config)
    logger.info("Done → %s  (open index.html, passphrase: %r)",
                out_dir, config["passphrase"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

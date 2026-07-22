"""Activity analytics: volumes, streaks, heatmaps, cumulative counts."""

from __future__ import annotations

from typing import Any

import pandas as pd

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _series_to_pairs(s: pd.Series) -> list[list[Any]]:
    return [[str(k), int(v)] for k, v in s.items()]


def compute_activity(df: pd.DataFrame) -> dict[str, Any]:
    """Compute daily/weekly/monthly volumes, streaks and hour/weekday patterns."""
    daily = df.groupby("date").size()
    daily.index = pd.to_datetime(daily.index)
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily_full = daily.reindex(full_range, fill_value=0)

    weekly = df.set_index("datetime").resample("W").size()
    monthly = df.groupby("month").size()

    per_sender_daily = {
        sender: _series_to_pairs(g.groupby("date").size())
        for sender, g in df.groupby("sender")
    }

    cumulative = daily_full.cumsum()

    # Streaks
    active = daily_full > 0
    streak_groups = (active != active.shift()).cumsum()
    streaks = active.groupby(streak_groups).agg(["sum", "size", "first"])
    active_runs = streaks[streaks["first"]]
    inactive_runs = streaks[~streaks["first"]]
    longest_streak = int(active_runs["size"].max()) if len(active_runs) else 0

    # Longest streak dates
    longest_streak_range = None
    if len(active_runs):
        gid = active_runs["size"].idxmax()
        run_days = daily_full[streak_groups == gid]
        longest_streak_range = [str(run_days.index.min().date()), str(run_days.index.max().date())]

    inactive_periods = []
    if len(inactive_runs):
        top = inactive_runs.nlargest(3, "size")
        for gid, row in top.iterrows():
            run_days = daily_full[streak_groups == gid]
            inactive_periods.append({
                "days": int(row["size"]),
                "from": str(run_days.index.min().date()),
                "to": str(run_days.index.max().date()),
            })

    hour_weekday = (
        df.groupby(["weekday", "hour"]).size()
        .unstack(fill_value=0)
        .reindex(index=range(7), columns=range(24), fill_value=0)
    )

    hourly = df.groupby("hour").size().reindex(range(24), fill_value=0)
    by_weekday = df.groupby("weekday").size().reindex(range(7), fill_value=0)

    night = df[(df["hour"] >= 22) | (df["hour"] < 5)]
    night_owl = {
        sender: round(len(g) / max(len(df[df["sender"] == sender]), 1) * 100, 1)
        for sender, g in night.groupby("sender")
    }
    morning = int(len(df[(df["hour"] >= 5) & (df["hour"] < 12)]))
    evening = int(len(df[(df["hour"] >= 17) & (df["hour"] < 22)]))

    hourly_by_sender = {
        sender: [int(x) for x in g.groupby("hour").size().reindex(range(24), fill_value=0)]
        for sender, g in df.groupby("sender")
    }

    busiest_day = daily_full.idxmax()

    return {
        "total_messages": int(len(df)),
        "total_days": int((daily_full.index.max() - daily_full.index.min()).days + 1),
        "active_days": int(active.sum()),
        "first_date": str(daily_full.index.min().date()),
        "last_date": str(daily_full.index.max().date()),
        "by_sender": {s: int(c) for s, c in df.groupby("sender").size().items()},
        "by_platform": {p: int(c) for p, c in df.groupby("platform").size().items()},
        "by_platform_sender": {
            f"{p}|{s}": int(c)
            for (p, s), c in df.groupby(["platform", "sender"]).size().items()
        },
        "daily": [[str(d.date()), int(v)] for d, v in daily_full.items()],
        "per_sender_daily": per_sender_daily,
        "weekly": [[str(d.date()), int(v)] for d, v in weekly.items()],
        "monthly": _series_to_pairs(monthly),
        "monthly_by_sender": {
            s: _series_to_pairs(g.groupby("month").size())
            for s, g in df.groupby("sender")
        },
        "cumulative": [[str(d.date()), int(v)] for d, v in cumulative.items()],
        "longest_streak_days": longest_streak,
        "longest_streak_range": longest_streak_range,
        "inactive_periods": inactive_periods,
        "hour_weekday_heatmap": hour_weekday.values.tolist(),
        "hourly": [int(x) for x in hourly],
        "hourly_by_sender": hourly_by_sender,
        "weekday": [int(x) for x in by_weekday],
        "weekday_labels": WEEKDAYS,
        "busiest_hour": int(hourly.idxmax()),
        "busiest_weekday": WEEKDAYS[int(by_weekday.idxmax())],
        "busiest_day": {"date": str(busiest_day.date()), "count": int(daily_full.max())},
        "night_owl_score": night_owl,
        "morning_vs_evening": {"morning": morning, "evening": evening},
        "avg_messages_per_active_day": round(len(df) / max(int(active.sum()), 1), 1),
    }

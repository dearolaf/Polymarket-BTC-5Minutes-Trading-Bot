"""Parse trade logs and compute performance statistics."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from easy_app.config import PROJECT_ROOT

LOG_PATH = PROJECT_ROOT / "log.txt"
PAPER_PATH = PROJECT_ROOT / "paper_trades.json"

_RESULT_RE = re.compile(
    r"slug_start_ts=(?P<ts>\d+)\s*\|\s*phase=(?P<phase>\w+)\s*\|"
    r".*?Order\s*:\s*(?P<order>UP|DOWN)\s*\|"
    r"\s*(?P<stake>\$[\d.]+)\s*\|"
    r"\s*Result\s*:\s*(?P<result>\w+)",
    re.IGNORECASE,
)


@dataclass
class TradeRecord:
    slug_ts: int
    phase: str
    order: str
    stake: str
    result: str
    won: Optional[bool] = None

    @property
    def is_scored(self) -> bool:
        return self.phase == "result" and self.result.upper() not in ("PENDING", "?")


@dataclass
class PerformanceStats:
    total_scored: int = 0
    wins: int = 0
    losses: int = 0
    pending: int = 0
    win_rate: float = 0.0
    current_streak: int = 0
    streak_type: str = "none"
    up_orders: int = 0
    down_orders: int = 0
    up_wins: int = 0
    down_wins: int = 0
    recent_results: List[str] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    chart_labels: List[str] = field(default_factory=list)
    chart_cumulative_wins: List[int] = field(default_factory=list)


def parse_log_line(line: str) -> Optional[TradeRecord]:
    m = _RESULT_RE.search(line.strip())
    if not m:
        return None
    order = m.group("order").upper()
    result = m.group("result").strip()
    rec = TradeRecord(
        slug_ts=int(m.group("ts")),
        phase=m.group("phase").lower(),
        order=order,
        stake=m.group("stake"),
        result=result,
    )
    if rec.is_scored:
        actual = result.upper()
        if actual in ("UP", "DOWN"):
            rec.won = order == actual
    return rec


def load_trades(log_path: Path = LOG_PATH) -> List[TradeRecord]:
    if not log_path.exists():
        return []
    trades: List[TradeRecord] = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        rec = parse_log_line(line)
        if rec:
            trades.append(rec)
    return trades


def compute_stats(
    trades: Optional[List[TradeRecord]] = None,
    last_n: int = 30,
) -> PerformanceStats:
    if trades is None:
        trades = load_trades()

    scored = [t for t in trades if t.is_scored]
    stats = PerformanceStats(trades=trades)

    for t in trades:
        if t.phase == "submit" and t.result.lower() == "pending":
            stats.pending += 1

    stats.total_scored = len(scored)
    for t in scored:
        if t.won:
            stats.wins += 1
        else:
            stats.losses += 1
        if t.order == "UP":
            stats.up_orders += 1
            if t.won:
                stats.up_wins += 1
        else:
            stats.down_orders += 1
            if t.won:
                stats.down_wins += 1

    decided = stats.wins + stats.losses
    if decided > 0:
        stats.win_rate = round(100.0 * stats.wins / decided, 1)

    recent = scored[-last_n:] if last_n else scored
    stats.recent_results = [
        "W" if t.won else "L" for t in recent
    ]

    streak = 0
    streak_type = "none"
    for t in reversed(scored):
        if not t.won and streak == 0 and streak_type == "none":
            streak_type = "loss"
            streak = 1
        elif streak_type == "loss" and not t.won:
            streak += 1
        elif streak_type == "loss" and t.won:
            break
        elif t.won and streak == 0 and streak_type == "none":
            streak_type = "win"
            streak = 1
        elif streak_type == "win" and t.won:
            streak += 1
        elif streak_type == "win" and not t.won:
            break
    stats.current_streak = streak
    stats.streak_type = streak_type

    cumulative = 0
    for i, t in enumerate(scored):
        if t.won:
            cumulative += 1
        stats.chart_labels.append(str(i + 1))
        stats.chart_cumulative_wins.append(cumulative)

    return stats


def format_uptime(started_at: Optional[str]) -> str:
    if not started_at:
        return "—"
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - start
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        mins, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {mins}m"
        if mins:
            return f"{mins}m {secs}s"
        return f"{secs}s"
    except (ValueError, TypeError):
        return "—"


def trades_to_table(trades: List[TradeRecord], limit: int = 50) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for t in reversed(trades[-limit:]):
        outcome = "—"
        if t.is_scored:
            outcome = "Win" if t.won else "Loss"
        elif t.result.lower() == "pending":
            outcome = "Pending"
        rows.append(
            {
                "Time (slug)": t.slug_ts,
                "Phase": t.phase,
                "Order": t.order,
                "Stake": t.stake,
                "Result": t.result.upper() if t.result else "—",
                "Outcome": outcome,
            }
        )
    return rows

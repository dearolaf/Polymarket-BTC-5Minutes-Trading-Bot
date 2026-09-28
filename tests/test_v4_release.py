"""Regression tests for v4.0.0 predictor and log parsing."""
from __future__ import annotations

from decimal import Decimal

import pytest

from easy_app.stats import compute_stats, parse_log_line, trades_to_table


def test_parse_log_line_result():
    line = (
        "slug_start_ts=1747143300 | phase=result | Time: 2026-05-12 10:55~2026-05-12 11:00 UTC | "
        "Order : DOWN | $10 | Result : UP"
    )
    rec = parse_log_line(line)
    assert rec is not None
    assert rec.won is False
    assert rec.order == "DOWN"


def test_compute_stats_win_rate():
    lines = [
        "slug_start_ts=1 | phase=result | Order : UP | $10 | Result : UP",
        "slug_start_ts=2 | phase=result | Order : UP | $10 | Result : DOWN",
    ]
    trades = [parse_log_line(line) for line in lines]
    trades = [t for t in trades if t]
    stats = compute_stats(trades)
    assert stats.wins == 1
    assert stats.losses == 1
    assert stats.win_rate == 50.0


def test_trades_to_table():
    line = "slug_start_ts=1 | phase=result | Order : UP | $10 | Result : UP"
    rec = parse_log_line(line)
    rows = trades_to_table([rec])
    assert rows[0]["Outcome"] == "Win"


def test_martingale_base_from_market_buy(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: True)
    monkeypatch.delenv("MARTINGALE_BASE_USD", raising=False)
    monkeypatch.setenv("MARKET_BUY_USD", "10.0")
    import importlib
    import bot

    importlib.reload(bot)
    assert bot.MARTINGALE_BASE_USD == Decimal("10")


def test_premium_plan_defaults(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: True)
    monkeypatch.setenv("BOT_PLAN", "premium")
    monkeypatch.delenv("PREDICTOR_MIN_SCORE", raising=False)
    monkeypatch.delenv("PREDICTOR_POLL_SECONDS", raising=False)
    monkeypatch.delenv("PREDICTOR_REQUIRE_TREND_ALIGN", raising=False)
    monkeypatch.delenv("PREDICTOR_REQUIRE_CANDLE_ALIGN", raising=False)
    import importlib
    import bot

    importlib.reload(bot)
    assert bot.IS_PREMIUM_PLAN is True
    assert bot.PREDICTOR_MIN_SCORE == 0.55
    assert bot.PREDICTOR_POLL_SECONDS == 3
    assert bot.PREDICTOR_REQUIRE_TREND_ALIGN is True

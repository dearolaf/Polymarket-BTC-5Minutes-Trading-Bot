"""
Polymarket gasless redemption via builder relayer.

Implementation lives in project-root ``polymarket_auto_redeem.py``; this module re-exports it
so ``bot.py`` can ``from execution.polymarket_auto_redeem import …``.
"""
from polymarket_auto_redeem import (  # noqa: F401
    fetch_redeemable_positions,
    redeem_once,
    start_auto_redeem_thread,
)

__all__ = [
    "fetch_redeemable_positions",
    "redeem_once",
    "start_auto_redeem_thread",
]

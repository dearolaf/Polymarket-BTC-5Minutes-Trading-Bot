"""
Polymarket **market** websocket sometimes delivers non-JSON frames (binary ping, null bytes, etc.).
Nautilus ``PolymarketDataClient._handle_raw_ws_message`` decodes with msgspec; on failure its
except handler formats ``f\"...{raw.decode()}...\"``, which raises again on invalid UTF-8 and can
break the reader loop so quote ticks stall.

This patch replaces ``_handle_raw_ws_message`` with a safe variant: ignore obvious non-JSON
payloads, decode with the same decoder, and log failures using ``errors='replace'`` only.
"""

import logging

logger = logging.getLogger(__name__)

_patch_applied = False


def apply_polymarket_market_ws_malformed_patch() -> bool:
    global _patch_applied
    if _patch_applied:
        return True

    try:
        from nautilus_trader.adapters.polymarket.data import PolymarketDataClient
    except ImportError as e:
        logger.warning(f"Polymarket market WS malformed patch skipped (import): {e}")
        return False

    def _patched_handle_raw_ws_message(self, raw: bytes) -> None:
        if not raw:
            return
        stripped = raw.lstrip()
        if not stripped:
            return
        # Skip binary / control frames; JSON market messages are objects or arrays.
        if stripped[:1] not in (b"{", b"["):
            return
        try:
            msg = self._decoder_market_msg.decode(raw)
        except Exception as e:
            preview = raw[:200].decode("utf-8", errors="replace")
            self._log.warning(
                f"Polymarket market WS: dropped non-decodable frame ({e.__class__.__name__}): {preview!r}"
            )
            return

        if isinstance(msg, list):
            for item in msg:
                self._handle_ws_message(item)
        else:
            self._handle_ws_message(msg)

    PolymarketDataClient._handle_raw_ws_message = _patched_handle_raw_ws_message
    _patch_applied = True
    logger.info("Polymarket market WS malformed-frame patch applied")
    return True

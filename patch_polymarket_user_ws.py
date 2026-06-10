"""
Polymarket user-channel websocket sometimes sends event_type=auto_redeem.
Nautilus decodes USER_WS_MESSAGE with msgspec; that union has no auto_redeem → ValidationError.


This patch wraps PolymarketExecutionClient._handle_ws_message so those messages are ignored
instead of logging ERROR + traceback on every redemption.
"""


import json
import logging


logger = logging.getLogger(__name__)


_patch_applied = False




def apply_polymarket_user_ws_patch() -> bool:
    global _patch_applied
    if _patch_applied:
        return True


    try:
        import msgspec
        from nautilus_trader.adapters.polymarket.execution import PolymarketExecutionClient
        from nautilus_trader.adapters.polymarket.schemas.user import PolymarketUserOrder
        from nautilus_trader.adapters.polymarket.schemas.user import PolymarketUserTrade
        from nautilus_trader.common.enums import LogColor
    except ImportError as e:
        logger.warning(f"Polymarket user WS patch skipped (import): {e}")
        return False


    def _patched_handle_ws_message(self, raw: bytes) -> None:
        try:
            if self._config.log_raw_ws_messages:
                self._log.info(
                    str(json.dumps(msgspec.json.decode(raw), indent=4)),
                    color=LogColor.MAGENTA,
                )


            try:
                msg = self._decoder_user_msg.decode(raw)
            except Exception as dec_err:
                txt = raw.decode(errors="replace")
                if "auto_redeem" in txt:
                    self._log.debug(
                        "Polymarket user WS: ignored auto_redeem (not in USER_WS_MESSAGE schema)"
                    )
                    return
                self._log.exception(
                    f"Error handling websocket message: {dec_err.__class__.__name__} - "
                    f"raw message: {txt}",
                    dec_err,
                )
                return


            if isinstance(msg, PolymarketUserOrder):
                self._handle_ws_order_msg(msg, wait_for_ack=True)
            elif isinstance(msg, PolymarketUserTrade):
                self._add_trade_to_cache(msg, raw)
                self._handle_ws_trade_msg(msg, wait_for_ack=True)
            else:
                self._log.error(f"Unrecognized websocket message {msg}")
        except Exception as e:
            self._log.exception(
                f"Error handling websocket message: {e.__class__.__name__} - "
                f"raw message: {raw.decode(errors='replace')}",
                e,
            )


    PolymarketExecutionClient._handle_ws_message = _patched_handle_ws_message
    _patch_applied = True
    logger.info("Polymarket user WS patch applied (auto_redeem messages ignored)")
    return True





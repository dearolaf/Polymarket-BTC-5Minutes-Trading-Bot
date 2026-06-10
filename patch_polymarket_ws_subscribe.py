"""
Nautilus PolymarketExecutionClient calls `_maintain_active_market` before each order,
which does `PolymarketWebSocketClient.subscribe(condition_id)`.


If the USER-channel WebSocket object still exists but is no longer active (idle drop,
network blip), `subscribe` skips reconnect (`client is not None`) and `_send` raises:


    RuntimeError: Cannot send text: connection not active


This patch wraps `subscribe` to disconnect and reconnect that client, then rely on
`_connect_client` → `_subscribe_all` to resync subscriptions.
"""


import logging


logger = logging.getLogger(__name__)


_patch_applied = False




def _is_dead_ws_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        part in msg
        for part in (
            "connection not active",
            "cannot send",
            "not connected",
            "connection closed",
            "websocket closed",
        )
    )




def apply_polymarket_ws_subscribe_patch() -> bool:
    global _patch_applied
    if _patch_applied:
        return True


    try:
        from nautilus_trader.adapters.polymarket.websocket.client import (
            PolymarketWebSocketClient,
        )
        from nautilus_trader.core.nautilus_pyo3 import WebSocketClientError
    except ImportError as e:
        logger.warning(f"Polymarket WS subscribe patch skipped (import): {e}")
        return False


    _orig = PolymarketWebSocketClient.subscribe


    async def subscribe(self, subscription: str) -> None:
        try:
            await _orig(self, subscription)
        except (RuntimeError, WebSocketClientError, OSError) as e:
            if not _is_dead_ws_error(e):
                raise
            client_id = self._get_client_for_subscription(subscription)
            logger.warning(
                "Polymarket WS subscribe failed (%s); reconnecting client %s for %s",
                e,
                client_id,
                subscription[:16] + "…" if len(subscription) > 16 else subscription,
            )
            if client_id < 0:
                raise
            await self._disconnect_client(client_id)
            await self._connect_client(client_id)


    subscribe.__doc__ = getattr(_orig, "__doc__", "")
    PolymarketWebSocketClient.subscribe = subscribe  # type: ignore[method-assign]


    _patch_applied = True
    logger.info("Polymarket WS subscribe reconnect patch applied")
    return True





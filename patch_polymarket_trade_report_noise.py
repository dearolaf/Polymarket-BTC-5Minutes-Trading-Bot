"""
Polymarket reconciliation walks wallet history for fills/orders. Only slug-loaded markets
exist in the instrument cache (short Gamma list → avoid HTTP 414). Nautilus logs every
skipped row at WARNING.


This patch:
  1) Wraps PolymarketExecutionClient.__init__ to filter `self._log.warning` so messages
     matching "Cannot handle trade/order report" + "instrument" + "not found" are dropped.
  2) Downgrades `self._log.error` to debug for "no venue order ID" status reports after a
     failed submit (expected when FAK never lands on the book).
  3) Replaces `_parse_trades_response_object` with a silent skip (no log) as a fallback
     if the logger cannot be wrapped.


Apply via bot.py and (redundantly) from patch_market_orders so it always runs with orders.
"""


import logging


logger = logging.getLogger(__name__)


_patch_applied = False
_ORIG_POLY_EXEC_INIT = None


_FILTER_ERROR_MARKERS = (
    "Cannot generate an order status report for Polymarket without the venue order ID",
)




def _should_drop_expected_missing_venue_error(args: tuple, kwargs: dict) -> bool:
    """After a failed submit there is no venue_order_id — reconciliation still asks for a report."""
    if not args:
        return False
    text = str(args[0])
    return any(m in text for m in _FILTER_ERROR_MARKERS)




_FILTER_MARKERS = (
    "Cannot handle trade report:",
    "Cannot handle order report:",
)




def _should_drop_missing_instrument_warning(args: tuple, kwargs: dict) -> bool:
    if not args:
        return False
    text = str(args[0])
    if "not found" not in text:
        return False
    if "instrument" not in text:
        return False
    return any(m in text for m in _FILTER_MARKERS)




def _install_warning_filter_on_exec_client(exec_client) -> None:
    log = exec_client._log
    if getattr(log, "_poly_exec_client_log_filters", False):
        return

    applied = False

    try:
        orig_error = log.error

        def filtered_error(*args, **kwargs):
            if _should_drop_expected_missing_venue_error(args, kwargs):
                if hasattr(log, "debug"):
                    return log.debug(*args, **kwargs)
                return None
            return orig_error(*args, **kwargs)

        log.error = filtered_error  # type: ignore[method-assign]
        applied = True
    except (TypeError, AttributeError):
        pass

    try:
        orig = log.warning

        def filtered_warning(*args, **kwargs):
            if _should_drop_missing_instrument_warning(args, kwargs):
                return None
            return orig(*args, **kwargs)

        log.warning = filtered_warning  # type: ignore[method-assign]
        applied = True
    except (TypeError, AttributeError):
        logger.debug("Could not wrap exec client log.warning (using parse fallback only)")

    if applied:
        setattr(log, "_poly_exec_client_log_filters", True)




def apply_polymarket_trade_report_noise_patch() -> bool:
    global _patch_applied, _ORIG_POLY_EXEC_INIT
    if _patch_applied:
        return True


    try:
        import msgspec
        from nautilus_trader.adapters.polymarket.execution import PolymarketExecutionClient
        from nautilus_trader.adapters.polymarket.common.symbol import get_polymarket_instrument_id
        from nautilus_trader.adapters.polymarket.common.types import JSON
        from nautilus_trader.core.uuid import UUID4
        from nautilus_trader.execution.messages import GenerateFillReports
        from nautilus_trader.execution.reports import FillReport
        from nautilus_trader.model.identifiers import ClientOrderId
        from nautilus_trader.model.identifiers import TradeId
        from nautilus_trader.model.identifiers import VenueOrderId
    except ImportError as e:
        logger.warning(f"Polymarket trade-report noise patch skipped (import): {e}")
        return False


    if _ORIG_POLY_EXEC_INIT is None:
        _ORIG_POLY_EXEC_INIT = PolymarketExecutionClient.__init__


    def _wrapped_init(self, *args, **kwargs):
        _ORIG_POLY_EXEC_INIT(self, *args, **kwargs)
        _install_warning_filter_on_exec_client(self)


    PolymarketExecutionClient.__init__ = _wrapped_init


    def _parse_trades_response_object(
        self,
        command: GenerateFillReports,
        json_obj: JSON,
        parsed_fill_keys: set[tuple[TradeId, VenueOrderId]],
        reports: list[FillReport],
    ) -> None:
        raw = msgspec.json.encode(json_obj)
        polymarket_trade = self._decoder_trade_report.decode(raw)


        filled_user_order_ids = polymarket_trade.get_filled_user_order_ids(
            self._wallet_address,
            self._api_key,
        )


        for order_id in filled_user_order_ids:
            asset_id = polymarket_trade.get_asset_id(order_id)
            instrument_id = get_polymarket_instrument_id(polymarket_trade.market, asset_id)


            if command.instrument_id is not None and instrument_id != command.instrument_id:
                continue


            instrument = self._cache.instrument(instrument_id)
            if instrument is None:
                continue


            venue_order_id = polymarket_trade.venue_order_id(order_id)


            if command.venue_order_id is not None and venue_order_id != command.venue_order_id:
                continue


            client_order_id = self._cache.client_order_id(venue_order_id)
            if client_order_id is None:
                client_order_id = ClientOrderId(str(UUID4()))


            report = polymarket_trade.parse_to_fill_report(
                account_id=self.account_id,
                instrument=instrument,
                client_order_id=client_order_id,
                ts_init=self._clock.timestamp_ns(),
                filled_user_order_id=order_id,
            )


            fill_key = (report.trade_id, report.venue_order_id)
            if fill_key in parsed_fill_keys:
                self._log.warning(f"Duplicate fill key {fill_key}, skipping")
                continue


            parsed_fill_keys.add(fill_key)
            reports.append(report)


    PolymarketExecutionClient._parse_trades_response_object = _parse_trades_response_object
    _patch_applied = True
    logger.info(
        "Polymarket missing-instrument noise patch applied "
        "(trade/order 'instrument not found' warnings suppressed; "
        "expected missing-venue status-report errors → DEBUG)"
    )
    return True





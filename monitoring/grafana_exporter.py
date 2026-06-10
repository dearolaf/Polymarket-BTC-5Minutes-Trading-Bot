"""
Grafana Metrics Exporter
Exports trading metrics in Prometheus format for Grafana
"""
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
)
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
from loguru import logger


import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


from monitoring.performance_tracker import get_performance_tracker
from execution.risk_engine import get_risk_engine
from execution.execution_engine import get_execution_engine




class MetricsHandler(BaseHTTPRequestHandler):
    """Custom HTTP handler that serves Prometheus metrics and handles Grafana queries."""
   
    exporter = None  # Will be set by the main class
   
    def do_GET(self):
        """Handle GET requests - serve metrics."""
        parsed = urllib.parse.urlparse(self.path)
       
        # Root path - show help
        if parsed.path == '/' or parsed.path == '':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <head><title>Polymarket Bot Metrics</title></head>
            <body>
            <h1>Polymarket Trading Bot Metrics</h1>
            <p>Metrics available at <a href="/metrics">/metrics</a></p>
            <p>Health check at <a href="/health">/health</a></p>
            </body>
            </html>
            """)
            return
       
        # Health check endpoint
        if parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
            return
       
        # Metrics endpoint - this is what Prometheus scrapes
        if parsed.path == '/metrics':
            try:
                # Generate metrics in Prometheus format
                metrics_data = generate_latest(REGISTRY)
               
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Accept, Content-Type')
                self.end_headers()
                self.wfile.write(metrics_data)
                return
               
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
                return
       
        # Handle Grafana's API probe (this fixes the 405 error)
        if parsed.path.startswith('/api/v1/'):
            # Return a minimal JSON response that Grafana accepts
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
           
            # For label queries, return empty list
            if 'labels' in parsed.path:
                self.wfile.write(b'{"status":"success","data":[]}')
            # For query requests, return empty result
            elif 'query' in parsed.path:
                self.wfile.write(b'{"status":"success","data":{"resultType":"vector","result":[]}}')
            # Default response
            else:
                self.wfile.write(b'{"status":"success"}')
            return
       
        # Handle CORS preflight
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")
   
    def do_POST(self):
        """Handle POST requests - forward to GET for metrics, handle API queries."""
        parsed = urllib.parse.urlparse(self.path)
       
        # Handle Grafana API probes
        if parsed.path.startswith('/api/v1/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
           
            # For label queries, return empty list
            if 'labels' in parsed.path:
                self.wfile.write(b'{"status":"success","data":[]}')
            # For query requests, return empty result
            elif 'query' in parsed.path:
                self.wfile.write(b'{"status":"success","data":{"resultType":"vector","result":[]}}')
            # Default response
            else:
                self.wfile.write(b'{"status":"success"}')
            return
       
        # For metrics endpoint, treat POST like GET
        if parsed.path == '/metrics':
            return self.do_GET()
       
        # Handle CORS preflight
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")
   
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Accept, Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.end_headers()
   
    def log_message(self, format, *args):
        """Override to avoid excessive logging."""
        try:
            # Check if args[1] exists and is a string that can be converted to int
            if len(args) >= 2:
                # The status code is the second argument, convert to int for comparison
                status_code = int(args[1]) if str(args[1]).isdigit() else 0
                if status_code >= 400:
                    logger.debug(f"Metrics server: {format % args}")
        except Exception:
            # If anything fails in logging, just ignore it
            pass




class GrafanaMetricsExporter:
    """
    Exports metrics to Prometheus/Grafana.
   
    Exposes metrics on HTTP endpoint for Grafana to scrape.
    Now handles Grafana's API probes correctly.
    """
   
    def __init__(
        self,
        port: int = 8000,
        update_interval: int = 5,  # seconds
    ):
        """
        Initialize metrics exporter.
       
        Args:
            port: HTTP port for metrics endpoint
            update_interval: How often to update metrics (seconds)
        """
        self.port = port
        self.update_interval = update_interval
       
        # Components
        self.performance = get_performance_tracker()
        self.risk = get_risk_engine()
        self.execution = get_execution_engine()
       
        # Prometheus metrics
        self._setup_metrics()
       
        # Server state
        self._is_running = False
        self._server = None
        self._thread = None
        self._update_thread: Optional[threading.Thread] = None
       
        logger.info(f"Initialized Grafana Metrics Exporter (port {port})")
   
    def _setup_metrics(self) -> None:
        """Setup Prometheus metrics."""
       
        # Performance metrics
        self.total_pnl = Gauge(
            'trading_total_pnl',
            'Total profit/loss in USD'
        )
       
        self.roi = Gauge(
            'trading_roi',
            'Return on investment as percentage'
        )
       
        self.win_rate = Gauge(
            'trading_win_rate',
            'Percentage of winning trades'
        )
       
        self.sharpe_ratio = Gauge(
            'trading_sharpe_ratio',
            'Sharpe ratio'
        )
       
        self.max_drawdown = Gauge(
            'trading_max_drawdown',
            'Maximum drawdown as percentage'
        )
       
        # Trade counters
        self.total_trades = Counter(
            'trades_total',
            'Total number of trades executed'
        )
       
        self.winning_trades = Counter(
            'trading_winning_trades',
            'Number of winning trades'
        )
       
        self.losing_trades = Counter(
            'trading_losing_trades',
            'Number of losing trades'
        )
       
        # Position metrics
        self.open_positions = Gauge(
            'trading_open_positions',
            'Number of currently open positions'
        )
       
        self.total_exposure = Gauge(
            'trading_total_exposure',
            'Total exposure in USD'
        )
       
        # Risk metrics
        self.risk_utilization = Gauge(
            'trading_risk_utilization',
            'Percentage of risk limits utilized'
        )
       
        self.current_capital = Gauge(
            'trading_current_capital',
            'Current account capital in USD'
        )
       
        # Signal metrics
        self.avg_signal_score = Gauge(
            'trading_avg_signal_score',
            'Average signal score (0-100)'
        )
       
        self.avg_signal_confidence = Gauge(
            'trading_avg_signal_confidence',
            'Average signal confidence (0-1)'
        )
       
        # Trade timing
        self.trade_duration = Histogram(
            'trading_trade_duration_seconds',
            'Trade duration in seconds',
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800]  # 1m to 8h
        )
       
        # Order metrics
        self.orders_placed = Counter(
            'trading_orders_placed',
            'Total orders placed'
        )
       
        self.orders_filled = Counter(
            'trading_orders_filled',
            'Total orders filled'
        )
       
        self.orders_rejected = Counter(
            'trading_orders_rejected',
            'Total orders rejected'
        )
       
        logger.info("Prometheus metrics initialized")
   
    def update_metrics(self) -> None:
        """Update all metrics with current values."""
        try:
            # Get performance metrics
            perf_metrics = self.performance.calculate_metrics()
           
            # Update gauges
            self.total_pnl.set(float(perf_metrics.total_pnl))
            self.roi.set(perf_metrics.roi * 100)
            self.win_rate.set(perf_metrics.win_rate * 100)
            self.sharpe_ratio.set(perf_metrics.sharpe_ratio)
            self.max_drawdown.set(perf_metrics.max_drawdown * 100)
           
            self.open_positions.set(perf_metrics.open_positions)
            self.total_exposure.set(float(perf_metrics.total_exposure))
           
            self.avg_signal_score.set(perf_metrics.avg_signal_score)
            self.avg_signal_confidence.set(perf_metrics.avg_signal_confidence)
           
            self.current_capital.set(float(self.performance.current_capital))
           
            # Get risk metrics
            risk_summary = self.risk.get_risk_summary()
           
            if risk_summary:
                self.risk_utilization.set(
                    risk_summary['exposure']['utilization_pct']
                )
           
            # Get execution stats
            exec_stats = self.execution.get_statistics()
           
            if exec_stats:
                # Update counters if needed
                pass
           
            logger.debug("Metrics updated successfully")
           
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
   
    def _run_update_loop(self) -> None:
        """Background metrics refresh (daemon thread — avoids orphan asyncio tasks)."""
        while self._is_running:
            try:
                self.update_metrics()
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
            # Short sleeps so stop() is picked up quickly
            for _ in range(max(1, self.update_interval * 10)):
                if not self._is_running:
                    return
                time.sleep(0.1)


    def start_sync(self) -> None:
        """Start metrics server and update loop (thread-safe; no asyncio)."""
        if self._is_running:
            logger.warning("Metrics exporter already running")
            return

        try:
            MetricsHandler.exporter = self

            self._server = HTTPServer(("0.0.0.0", self.port), MetricsHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

            logger.info(f"✓ Metrics server started on port {self.port}")
            logger.info(f"  Metrics available at: http://localhost:{self.port}/metrics")
            logger.info(f"  Health check: http://localhost:{self.port}/health")
            logger.info(f"  Supports: GET, POST, OPTIONS")

            self._is_running = True

            self._update_thread = threading.Thread(
                target=self._run_update_loop,
                daemon=True,
                name="GrafanaMetricsUpdate",
            )
            self._update_thread.start()

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            self._is_running = False

    async def start(self) -> None:
        """Start metrics server (async wrapper for callers that expect a coroutine)."""
        self.start_sync()

    def stop_sync(self) -> None:
        """Stop metrics server (thread-safe; use from on_stop / sync shutdown paths)."""
        self._is_running = False

        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=self.update_interval + 2.0)
        self._update_thread = None

        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

        logger.info("Metrics exporter stopped")

    async def stop(self) -> None:
        """Stop metrics server (async wrapper)."""
        self.stop_sync()
   
    def increment_trade_counter(self, won: bool) -> None:
        """
        Increment trade counter.
       
        Args:
            won: True if trade was profitable
        """
        self.total_trades.inc()
       
        if won:
            self.winning_trades.inc()
        else:
            self.losing_trades.inc()
   
    def record_trade_duration(self, duration_seconds: float) -> None:
        """
        Record trade duration.
       
        Args:
            duration_seconds: Duration in seconds
        """
        self.trade_duration.observe(duration_seconds)
   
    def increment_order_counter(self, status: str) -> None:
        """
        Increment order counter.
       
        Args:
            status: "placed", "filled", or "rejected"
        """
        if status == "placed":
            self.orders_placed.inc()
        elif status == "filled":
            self.orders_filled.inc()
        elif status == "rejected":
            self.orders_rejected.inc()




# Singleton instance
_grafana_exporter_instance = None


def get_grafana_exporter() -> GrafanaMetricsExporter:
    """Get singleton Grafana exporter."""
    global _grafana_exporter_instance
    if _grafana_exporter_instance is None:
        _grafana_exporter_instance = GrafanaMetricsExporter()
    return _grafana_exporter_instance




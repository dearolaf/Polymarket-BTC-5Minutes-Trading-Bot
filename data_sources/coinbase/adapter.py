"""
Coinbase Data Source Adapter
Fetches BTC price data from Coinbase Pro API
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import httpx
from loguru import logger


class CoinbaseDataSource:
    """
    Coinbase Pro API data source for BTC price data.
    
    Provides:
    - Real-time BTC price
    - Order book data
    - Recent trades
    - 24h statistics
    """
    
    def __init__(
        self,
        base_url: str = "https://api.exchange.coinbase.com",
        product_id: str = "BTC-USD",
    ):
        """
        Initialize Coinbase data source.
        
        Args:
            base_url: Coinbase Pro API base URL
            product_id: Trading pair (default: BTC-USD)
        """
        self.base_url = base_url
        self.product_id = product_id
        self.session: Optional[httpx.AsyncClient] = None
        
        # Cache
        self._last_price: Optional[Decimal] = None
        self._last_update: Optional[datetime] = None
        
        logger.info(f"Initialized Coinbase data source for {product_id}")
    
    async def connect(self) -> bool:
        """
        Connect to Coinbase API.
        
        Returns:
            True if connection successful
        """
        try:
            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={
                    "User-Agent": "PolymarketBot/1.0",
                    "Accept": "application/json",
                }
            )
            
            # Test connection
            response = await self.session.get(f"/products/{self.product_id}")
            response.raise_for_status()
            
            logger.info("✓ Connected to Coinbase API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Coinbase: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection and drop the client so the next call can reconnect."""
        if self.session:
            try:
                await self.session.aclose()
            except Exception:
                pass
            self.session = None
            logger.info("Disconnected from Coinbase API")

    async def _ensure_session(self) -> bool:
        if self.session is not None:
            return True
        return await self.connect()

    async def get_current_price(self) -> Optional[Decimal]:
        """
        Get current BTC price.
        
        Returns:
            Current price or None if error
        """
        if not await self._ensure_session():
            return None
        try:
            response = await self.session.get(f"/products/{self.product_id}/ticker")
            response.raise_for_status()
            
            data = response.json()
            price = Decimal(str(data["price"]))
            
            self._last_price = price
            self._last_update = datetime.now()
            
            logger.debug(f"Coinbase BTC price: ${price:,.2f}")
            return price
            
        except Exception as e:
            logger.error(f"Error fetching Coinbase price: {e}")
            await self.disconnect()
            return None
    
    async def get_order_book(self, level: int = 2) -> Optional[Dict[str, Any]]:
        """
        Get order book data.
        
        Args:
            level: 1=best bid/ask, 2=top 50, 3=full book
            
        Returns:
            Order book dict with bids and asks
        """
        if not await self._ensure_session():
            return None
        try:
            response = await self.session.get(
                f"/products/{self.product_id}/book",
                params={"level": level}
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "timestamp": datetime.now(),
                "bids": [
                    {"price": Decimal(b[0]), "size": Decimal(b[1])}
                    for b in data.get("bids", [])
                ],
                "asks": [
                    {"price": Decimal(a[0]), "size": Decimal(a[1])}
                    for a in data.get("asks", [])
                ],
            }
            
        except Exception as e:
            logger.error(f"Error fetching Coinbase order book: {e}")
            await self.disconnect()
            return None
    
    async def get_24h_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get 24-hour statistics.
        
        Returns:
            Dict with open, high, low, volume, etc.
        """
        if not await self._ensure_session():
            return None
        try:
            response = await self.session.get(f"/products/{self.product_id}/stats")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "timestamp": datetime.now(),
                "open": Decimal(str(data["open"])),
                "high": Decimal(str(data["high"])),
                "low": Decimal(str(data["low"])),
                "volume": Decimal(str(data["volume"])),
                "last": Decimal(str(data["last"])),
            }
            
        except Exception as e:
            logger.error(f"Error fetching Coinbase 24h stats: {e}")
            await self.disconnect()
            return None
    
    async def get_recent_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of recent trades
        """
        if not await self._ensure_session():
            return []
        try:
            response = await self.session.get(
                f"/products/{self.product_id}/trades",
                params={"limit": limit}
            )
            response.raise_for_status()
            
            data = response.json()
            
            trades = []
            for trade in data[:limit]:
                trades.append({
                    "timestamp": datetime.fromisoformat(trade["time"].replace("Z", "+00:00")),
                    "trade_id": trade["trade_id"],
                    "price": Decimal(str(trade["price"])),
                    "size": Decimal(str(trade["size"])),
                    "side": trade["side"],  # "buy" or "sell"
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching Coinbase trades: {e}")
            await self.disconnect()
            return []
    
    async def get_candles(
        self,
        granularity: int = 300,  # 5 minutes
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical candles (OHLCV data).
        
        Args:
            granularity: Candle size in seconds (60, 300, 900, 3600, 21600, 86400)
            limit: Number of candles to return
            
        Returns:
            List of candle data
        """
        if not await self._ensure_session():
            return []
        try:
            response = await self.session.get(
                f"/products/{self.product_id}/candles",
                params={"granularity": granularity}
            )
            response.raise_for_status()
            
            data = response.json()
            
            candles = []
            for candle in data[:limit]:
                # Format: [time, low, high, open, close, volume]
                candles.append({
                    "timestamp": datetime.fromtimestamp(candle[0]),
                    "open": Decimal(str(candle[3])),
                    "high": Decimal(str(candle[2])),
                    "low": Decimal(str(candle[1])),
                    "close": Decimal(str(candle[4])),
                    "volume": Decimal(str(candle[5])),
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching Coinbase candles: {e}")
            await self.disconnect()
            return []

    async def fetch_candle_open_close_for_bucket(
        self,
        bucket_start_unix: int,
        granularity: int = 300,
        max_retries: int = 8,
        retry_delay_sec: float = 1.0,
    ) -> Optional[Tuple[Decimal, Decimal]]:
        """
        Return (open, close) for the candle whose bucket start equals ``bucket_start_unix``.

        Coinbase returns rows as ``[time, low, high, open, close, volume]`` (``time`` = bucket start).
        The bucket covers ``[bucket_start_unix, bucket_start_unix + granularity)``.

        Retries help when the interval just closed and the last candle is not listed yet.
        """
        end_param = bucket_start_unix + granularity
        for attempt in range(max_retries):
            if not await self._ensure_session():
                return None
            try:
                response = await self.session.get(
                    f"/products/{self.product_id}/candles",
                    params={
                        "granularity": granularity,
                        "start": bucket_start_unix,
                        "end": end_param,
                    },
                )
                response.raise_for_status()
                data = response.json()
                for row in data:
                    try:
                        t0 = int(row[0])
                    except (TypeError, ValueError, IndexError):
                        continue
                    if t0 != bucket_start_unix:
                        continue
                    # [time, low, high, open, close, volume]
                    open_px = Decimal(str(row[3]))
                    close_px = Decimal(str(row[4]))
                    return (open_px, close_px)
            except Exception as e:
                logger.warning(
                    f"Coinbase candle fetch attempt {attempt + 1}/{max_retries} "
                    f"for bucket={bucket_start_unix}: {e}"
                )
                await self.disconnect()
            if attempt + 1 < max_retries:
                await asyncio.sleep(retry_delay_sec)
        return None

    @property
    def last_price(self) -> Optional[Decimal]:
        """Get cached last price."""
        return self._last_price
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get time of last price update."""
        return self._last_update
    
    async def health_check(self) -> bool:
        """
        Check if data source is healthy.
        
        Returns:
            True if healthy
        """
        try:
            price = await self.get_current_price()
            return price is not None
        except:
            return False


# Singleton instance for easy import
_coinbase_instance: Optional[CoinbaseDataSource] = None

def get_coinbase_source() -> CoinbaseDataSource:
    """Get singleton instance of Coinbase data source."""
    global _coinbase_instance
    if _coinbase_instance is None:
        _coinbase_instance = CoinbaseDataSource()
    return _coinbase_instance
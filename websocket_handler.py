"""
WebSocket handler for real-time price data from Binance
"""

import logging
import asyncio
import json
import time
from typing import Dict, List, Callable, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handle real-time price data via WebSocket (simplified implementation)"""
    
    def __init__(self, binance_client):
        self.binance_client = binance_client
        self.price_callbacks: List[Callable] = []
        self.current_prices: Dict[str, Dict] = {}
        self.is_running = False
        self.price_fetch_task = None
        
    def start(self, symbols: List[str]):
        """Start price monitoring for given symbols"""
        try:
            if not self.binance_client.sync_client:
                logger.error("Binance sync client not initialized")
                return False
            
            self.is_running = True
            self.symbols = symbols
            
            # Start price fetching task
            self.price_fetch_task = asyncio.create_task(self._fetch_prices_loop())
            
            logger.info(f"Price monitoring started for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error starting price monitoring: {e}")
            return False
    
    async def _fetch_prices_loop(self):
        """Continuously fetch prices for monitored symbols"""
        while self.is_running:
            try:
                if self.binance_client.sync_client:
                    # Get ticker prices for all symbols
                    tickers = self.binance_client.sync_client.futures_symbol_ticker()
                    
                    # Update prices for monitored symbols
                    for ticker in tickers:
                        symbol = ticker['symbol']
                        if symbol in self.symbols:
                            price_data = {
                                'symbol': symbol,
                                'price': float(ticker['price']),
                                'timestamp': int(time.time() * 1000)
                            }
                            
                            self.current_prices[symbol] = price_data
                            self.binance_client._current_prices[symbol] = price_data['price']
                            
                            # Call registered callbacks
                            for callback in self.price_callbacks:
                                try:
                                    callback(symbol, price_data)
                                except Exception as e:
                                    logger.error(f"Error in price callback: {e}")
                
                # Sleep for 1 second before next fetch
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching prices: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    

    

    
    def add_price_callback(self, callback: Callable):
        """Add a callback function for price updates"""
        self.price_callbacks.append(callback)
    
    def remove_price_callback(self, callback: Callable):
        """Remove a callback function"""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        price_data = self.current_prices.get(symbol)
        if price_data:
            return price_data.get('price')
        return None
    
    def get_current_data(self, symbol: str) -> Optional[Dict]:
        """Get current price data for a symbol"""
        return self.current_prices.get(symbol)
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all current prices"""
        return {symbol: data.get('price', 0) for symbol, data in self.current_prices.items()}
    
    def add_symbol(self, symbol: str):
        """Add a new symbol to monitoring"""
        try:
            if symbol not in self.symbols:
                self.symbols.append(symbol)
                logger.info(f"Added {symbol} to price monitoring")
            else:
                logger.info(f"{symbol} is already being monitored")
                
        except Exception as e:
            logger.error(f"Error adding symbol {symbol}: {e}")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring"""
        try:
            if symbol in self.symbols:
                self.symbols.remove(symbol)
            
            # Remove from price cache
            if symbol in self.current_prices:
                del self.current_prices[symbol]
            
            logger.info(f"Removed {symbol} from price monitoring")
            
        except Exception as e:
            logger.error(f"Error removing symbol {symbol}: {e}")
    
    def stop(self):
        """Stop price monitoring"""
        try:
            self.is_running = False
            
            # Cancel price fetch task
            if self.price_fetch_task:
                self.price_fetch_task.cancel()
            
            self.current_prices.clear()
            
            # Close socket manager
            if self.socket_manager:
                # The socket manager will close when the async context managers exit
                self.socket_manager = None
            
            logger.info("WebSocket handler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket handler: {e}")
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and running"""
        return self.is_running and len(self.streams) > 0
    
    async def reconnect(self, symbols: List[str]):
        """Reconnect WebSocket streams"""
        try:
            logger.info("Reconnecting WebSocket streams...")
            await self.stop()
            await asyncio.sleep(2)  # Small delay
            await self.start(symbols)
            
        except Exception as e:
            logger.error(f"Error reconnecting WebSocket: {e}")
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all streams"""
        status = {}
        for stream_key in self.streams.keys():
            # Extract symbol from stream key
            symbol = stream_key.split('_')[0]
            status[symbol] = self.is_running
        
        return status

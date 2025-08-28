"""
WebSocket handler for real-time price data from Binance
"""

import logging
import asyncio
import json
from typing import Dict, List, Callable, Optional
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handle real-time price data via WebSocket"""
    
    def __init__(self, binance_client):
        self.binance_client = binance_client
        self.socket_manager: Optional[BinanceSocketManager] = None
        self.streams = {}
        self.price_callbacks: List[Callable] = []
        self.current_prices: Dict[str, Dict] = {}
        self.is_running = False
        
    async def start(self, symbols: List[str]):
        """Start WebSocket connections for given symbols"""
        try:
            if not self.binance_client.client:
                logger.error("Binance client not initialized")
                return False
            
            self.socket_manager = BinanceSocketManager(self.binance_client.client)
            self.is_running = True
            
            # Start individual ticker streams
            for symbol in symbols:
                await self.start_symbol_stream(symbol)
            
            logger.info(f"WebSocket streams started for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error starting WebSocket streams: {e}")
            return False
    
    async def start_symbol_stream(self, symbol: str):
        """Start WebSocket stream for a single symbol"""
        try:
            # Start ticker stream
            ticker_stream = self.socket_manager.symbol_ticker_socket(symbol)
            self.streams[f"{symbol}_ticker"] = ticker_stream
            
            # Start the stream processing task
            asyncio.create_task(self.process_ticker_stream(ticker_stream, symbol))
            
            # Start kline stream for 1-minute data
            kline_stream = self.socket_manager.kline_socket(symbol, "1m")
            self.streams[f"{symbol}_kline"] = kline_stream
            
            # Start the kline processing task
            asyncio.create_task(self.process_kline_stream(kline_stream, symbol))
            
            logger.info(f"Started WebSocket streams for {symbol}")
            
        except Exception as e:
            logger.error(f"Error starting stream for {symbol}: {e}")
    
    async def process_ticker_stream(self, stream, symbol: str):
        """Process ticker WebSocket messages"""
        try:
            async with stream as ticker_socket:
                while self.is_running:
                    try:
                        msg = await ticker_socket.recv()
                        await self.handle_ticker_message(msg, symbol)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error processing ticker message for {symbol}: {e}")
                        await asyncio.sleep(1)
                        
        except Exception as e:
            logger.error(f"Error in ticker stream for {symbol}: {e}")
        finally:
            logger.info(f"Ticker stream closed for {symbol}")
    
    async def process_kline_stream(self, stream, symbol: str):
        """Process kline WebSocket messages"""
        try:
            async with stream as kline_socket:
                while self.is_running:
                    try:
                        msg = await kline_socket.recv()
                        await self.handle_kline_message(msg, symbol)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error processing kline message for {symbol}: {e}")
                        await asyncio.sleep(1)
                        
        except Exception as e:
            logger.error(f"Error in kline stream for {symbol}: {e}")
        finally:
            logger.info(f"Kline stream closed for {symbol}")
    
    async def handle_ticker_message(self, msg: Dict, symbol: str):
        """Handle ticker WebSocket message"""
        try:
            if not isinstance(msg, dict):
                return
            
            # Update current prices
            price_data = {
                'symbol': msg.get('s', symbol),
                'price': float(msg.get('c', 0)),
                'price_change': float(msg.get('P', 0)),
                'price_change_percent': float(msg.get('P', 0)),
                'high': float(msg.get('h', 0)),
                'low': float(msg.get('l', 0)),
                'volume': float(msg.get('v', 0)),
                'timestamp': msg.get('E', 0)
            }
            
            self.current_prices[symbol] = price_data
            
            # Update binance client cache
            self.binance_client._current_prices[symbol] = price_data['price']
            
            # Call registered callbacks
            for callback in self.price_callbacks:
                try:
                    await callback(symbol, price_data)
                except Exception as e:
                    logger.error(f"Error in price callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling ticker message for {symbol}: {e}")
    
    async def handle_kline_message(self, msg: Dict, symbol: str):
        """Handle kline WebSocket message"""
        try:
            if not isinstance(msg, dict) or 'k' not in msg:
                return
            
            kline = msg['k']
            
            # Only process closed klines (completed candles)
            if not kline.get('x', False):
                return
            
            kline_data = {
                'symbol': kline.get('s', symbol),
                'open_time': kline.get('t', 0),
                'close_time': kline.get('T', 0),
                'open': float(kline.get('o', 0)),
                'high': float(kline.get('h', 0)),
                'low': float(kline.get('l', 0)),
                'close': float(kline.get('c', 0)),
                'volume': float(kline.get('v', 0)),
                'number_of_trades': kline.get('n', 0)
            }
            
            logger.debug(f"Received completed kline for {symbol}: {kline_data['close']}")
            
        except Exception as e:
            logger.error(f"Error handling kline message for {symbol}: {e}")
    
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
    
    async def add_symbol(self, symbol: str):
        """Add a new symbol to monitoring"""
        try:
            if f"{symbol}_ticker" not in self.streams:
                await self.start_symbol_stream(symbol)
                logger.info(f"Added {symbol} to WebSocket monitoring")
            else:
                logger.info(f"{symbol} is already being monitored")
                
        except Exception as e:
            logger.error(f"Error adding symbol {symbol}: {e}")
    
    async def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring"""
        try:
            # Close ticker stream
            ticker_key = f"{symbol}_ticker"
            if ticker_key in self.streams:
                # Note: BinanceSocketManager doesn't have a direct close method for individual streams
                # The stream will close when the context manager exits
                del self.streams[ticker_key]
            
            # Close kline stream
            kline_key = f"{symbol}_kline"
            if kline_key in self.streams:
                del self.streams[kline_key]
            
            # Remove from price cache
            if symbol in self.current_prices:
                del self.current_prices[symbol]
            
            logger.info(f"Removed {symbol} from WebSocket monitoring")
            
        except Exception as e:
            logger.error(f"Error removing symbol {symbol}: {e}")
    
    async def stop(self):
        """Stop all WebSocket connections"""
        try:
            self.is_running = False
            
            # Clear streams
            self.streams.clear()
            
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

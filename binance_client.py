"""
Binance API client wrapper for futures trading
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from binance.client import Client, AsyncClient
from binance.streams import BinanceSocketManager
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
import json

logger = logging.getLogger(__name__)

class BinanceClient:
    """Wrapper for Binance API with futures trading capabilities"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client: Optional[AsyncClient] = None
        self.sync_client: Optional[Client] = None
        self.socket_manager: Optional[BinanceSocketManager] = None
        self._current_prices: Dict[str, float] = {}
        self._loop = None
        
    def _get_or_create_loop(self):
        """Get current event loop or create a new one"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop for this thread
                import threading
                if threading.current_thread() != threading.main_thread():
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                    return self._loop
                return loop
            else:
                return loop
        except RuntimeError:
            # No event loop, create new one
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            return self._loop
        
    async def initialize(self) -> bool:
        """Initialize the Binance client"""
        try:
            # Initialize async client for WebSocket
            self.client = await AsyncClient.create(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            
            # Initialize sync client for API calls
            self.sync_client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            
            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Binance {'Testnet' if self.testnet else 'Mainnet'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            return False
    
    async def close(self):
        """Close the client connection"""
        if self.client:
            await self.client.close_connection()
    
    def get_account_balance_sync(self) -> Dict[str, float]:
        """Get futures account balance (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return {}
                
            account_info = self.sync_client.futures_account()
            balances = {}
            
            for balance in account_info['assets']:
                asset = balance['asset']
                free_balance = float(balance['availableBalance'])
                if free_balance > 0:
                    balances[asset] = free_balance
            
            return balances
            
        except BinanceAPIException as e:
            logger.error(f"API error getting balance: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get futures account balance"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return {}
                
            account_info = await self.client.futures_account()
            balances = {}
            
            for balance in account_info['assets']:
                asset = balance['asset']
                free_balance = float(balance['availableBalance'])
                if free_balance > 0:
                    balances[asset] = free_balance
            
            return balances
            
        except BinanceAPIException as e:
            logger.error(f"API error getting balance: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}
    
    def get_usdt_balance_sync(self) -> float:
        """Get USDT balance specifically (synchronous)"""
        try:
            balances = self.get_account_balance_sync()
            return balances.get('USDT', 0.0)
        except Exception as e:
            logger.error(f"Error getting USDT balance: {e}")
            return 0.0
    
    async def get_usdt_balance(self) -> float:
        """Get USDT balance specifically"""
        try:
            balances = await self.get_account_balance()
            return balances.get('USDT', 0.0)
        except Exception as e:
            logger.error(f"Error getting USDT balance: {e}")
            return 0.0
    
    def get_current_price_sync(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return None
                
            ticker = self.sync_client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self._current_prices[symbol] = price
            return price
            
        except BinanceAPIException as e:
            logger.error(f"API error getting price for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return None
                
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self._current_prices[symbol] = price
            return price
            
        except BinanceAPIException as e:
            logger.error(f"API error getting price for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_klines_sync(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """Get kline/candlestick data (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return []
                
            klines = self.sync_client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to more readable format
            formatted_klines = []
            for kline in klines:
                formatted_klines.append({
                    'open_time': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_asset_volume': float(kline[7]),
                    'number_of_trades': kline[8],
                    'taker_buy_base_asset_volume': float(kline[9]),
                    'taker_buy_quote_asset_volume': float(kline[10])
                })
            
            return formatted_klines
            
        except BinanceAPIException as e:
            logger.error(f"API error getting klines for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def get_exchange_symbols_sync(self) -> List[str]:
        """Get all available USDT futures symbols (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return []
                
            exchange_info = self.sync_client.futures_exchange_info()
            usdt_symbols = []
            
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                if (symbol.endswith('USDT') and 
                    symbol_info['status'] == 'TRADING' and
                    symbol_info['contractType'] == 'PERPETUAL'):
                    usdt_symbols.append(symbol)
            
            # Sort symbols alphabetically
            usdt_symbols.sort()
            logger.info(f"Found {len(usdt_symbols)} USDT perpetual futures symbols")
            return usdt_symbols
            
        except BinanceAPIException as e:
            logger.error(f"API error getting exchange symbols: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting exchange symbols: {e}")
            return []

    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """Get kline/candlestick data"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return []
                
            klines = await self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to more readable format
            formatted_klines = []
            for kline in klines:
                formatted_klines.append({
                    'open_time': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_asset_volume': float(kline[7]),
                    'number_of_trades': kline[8],
                    'taker_buy_base_asset_volume': float(kline[9]),
                    'taker_buy_quote_asset_volume': float(kline[10])
                })
            
            return formatted_klines
            
        except BinanceAPIException as e:
            logger.error(f"API error getting klines for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def place_market_order_sync(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place a market order (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return None
            
            # Get current price to validate order value
            current_price = self.get_current_price_sync(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return None
                
            # Check minimum notional (order value must be >= $20)
            order_value = quantity * current_price
            if order_value < 20.0:
                logger.error(f"Order value too small: ${order_value:.2f} < $20.00 (minimum)")
                return None
                
            order = self.sync_client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            
            logger.info(f"Market order placed: {side} {quantity} {symbol}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None

    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place a market order"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return None
                
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            
            logger.info(f"Market order placed: {side} {quantity} {symbol}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    def place_limit_order_sync(self, symbol: str, side: str, quantity: float, price: float) -> Optional[Dict]:
        """Place a limit order (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return None
                
            # Round price to proper precision
            rounded_price = self.round_price_to_precision(symbol, price)
            
            order = self.sync_client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=rounded_price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            
            logger.info(f"Limit order placed: {side} {quantity} {symbol} at {price}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing limit order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    async def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Optional[Dict]:
        """Place a limit order"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return None
                
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            
            logger.info(f"Limit order placed: {side} {quantity} {symbol} at {price}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    def place_stop_loss_order_sync(self, symbol: str, side: str, quantity: float, stop_price: float) -> Optional[Dict]:
        """Place a stop-loss order (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return None
            
            # Get current price to validate stop price
            current_price = self.get_current_price_sync(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return None
            
            # Validate stop price is reasonable (within 10% of current price)
            price_diff_percent = abs(stop_price - current_price) / current_price * 100
            if price_diff_percent > 10:
                logger.warning(f"Stop price {stop_price} too far from current {current_price} ({price_diff_percent:.1f}%)")
                # Adjust stop price to be within acceptable range
                if side == 'SELL':  # Stop loss for long position
                    stop_price = current_price * 0.95  # 5% below current
                else:  # Stop loss for short position  
                    stop_price = current_price * 1.05  # 5% above current
                logger.info(f"Adjusted stop price to {stop_price}")
                
            # Round stop price to proper precision
            rounded_stop_price = self.round_price_to_precision(symbol, stop_price)
            
            order = self.sync_client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=rounded_stop_price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            
            logger.info(f"Stop-loss order placed: {side} {quantity} {symbol} at {stop_price}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing stop-loss: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing stop-loss order: {e}")
            return None

    async def place_stop_loss_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> Optional[Dict]:
        """Place a stop-loss order"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return None
                
            # Round stop price to proper precision  
            rounded_stop_price = self.round_price_to_precision(symbol, stop_price)
            
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=rounded_stop_price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            
            logger.info(f"Stop-loss order placed: {side} {quantity} {symbol} at {stop_price}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order error: {e}")
            return None
        except BinanceAPIException as e:
            logger.error(f"API error placing stop-loss: {e}")
            return None
        except Exception as e:
            logger.error(f"Error placing stop-loss order: {e}")
            return None
    
    def get_open_orders_sync(self, symbol: str = None) -> List[Dict]:
        """Get all open orders (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return []
                
            if symbol:
                orders = self.sync_client.futures_get_open_orders(symbol=symbol)
            else:
                orders = self.sync_client.futures_get_open_orders()
                
            return orders
            
        except BinanceAPIException as e:
            logger.error(f"API error getting orders: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def cancel_order_sync(self, symbol: str, order_id: str) -> bool:
        """Cancel an order (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return False
                
            self.sync_client.futures_cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order {order_id} cancelled for {symbol}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"API error cancelling order: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return False
                
            await self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order {order_id} cancelled for {symbol}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"API error cancelling order: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_open_positions_sync(self) -> List[Dict]:
        """Get all open positions (synchronous)"""
        try:
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return []
                
            positions = self.sync_client.futures_position_information()
            open_positions = []
            
            for position in positions:
                position_amt = float(position['positionAmt'])
                if position_amt != 0:
                    open_positions.append({
                        'symbol': position['symbol'],
                        'position_amt': position_amt,
                        'entry_price': float(position['entryPrice']),
                        'unrealized_pnl': float(position['unRealizedProfit']),
                        'percentage': float(position.get('percentage', 0.0)),
                        'side': 'LONG' if position_amt > 0 else 'SHORT'
                    })
            
            return open_positions
            
        except BinanceAPIException as e:
            logger.error(f"API error getting positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            if not self.client:
                logger.error("Client not initialized")
                return []
                
            positions = await self.client.futures_position_information()
            open_positions = []
            
            for position in positions:
                position_amt = float(position['positionAmt'])
                if position_amt != 0:
                    open_positions.append({
                        'symbol': position['symbol'],
                        'position_amt': position_amt,
                        'entry_price': float(position['entryPrice']),
                        'unrealized_pnl': float(position['unRealizedProfit']),
                        'percentage': float(position.get('percentage', 0.0)),
                        'side': 'LONG' if position_amt > 0 else 'SHORT'
                    })
            
            return open_positions
            
        except BinanceAPIException as e:
            logger.error(f"API error getting positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def calculate_quantity_from_usdt_sync(self, symbol: str, usdt_amount: float) -> Optional[float]:
        """Calculate quantity based on USDT amount (synchronous)"""
        try:
            price = self.get_current_price_sync(symbol)
            if price is None:
                return None
            
            # Get symbol info for precision
            if not self.sync_client:
                logger.error("Sync client not initialized")
                return None
                
            exchange_info = self.sync_client.futures_exchange_info()
            symbol_info = None
            
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    symbol_info = s
                    break
            
            if symbol_info is None:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            # Calculate quantity
            quantity = usdt_amount / price
            
            # Round to proper precision
            for filter_info in symbol_info['filters']:
                if filter_info['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_info['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = round(quantity, precision)
                    break
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculating quantity: {e}")
            return None
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        """Get cached price for a symbol"""
        return self._current_prices.get(symbol)
    
    def round_price_to_precision(self, symbol: str, price: float) -> float:
        """Round price to symbol's tick size precision"""
        try:
            if not self.sync_client:
                return round(price, 6)
                
            exchange_info = self.sync_client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    for filter_info in s['filters']:
                        if filter_info['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_info['tickSize'])
                            if tick_size >= 1:
                                precision = 0
                            else:
                                precision = len(str(tick_size).split('.')[-1].rstrip('0'))
                            return round(price, precision)
                    break
            return round(price, 6)
        except Exception as e:
            logger.error(f"Error rounding price for {symbol}: {e}")
            return round(price, 6)

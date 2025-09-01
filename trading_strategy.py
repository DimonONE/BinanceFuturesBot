"""
Trading strategy implementation with trend following and position averaging
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class TrendDirection(Enum):
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ADD_POSITION = "ADD_POSITION"

@dataclass
class TradingSignal:
    symbol: str
    signal_type: SignalType
    confidence: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""

class TrendFollowingStrategy:
    """Trend following strategy with smart position averaging"""
    
    def __init__(self, binance_client, config, data_storage=None):
        self.binance_client = binance_client
        self.config = config
        self.data_storage = data_storage
        self.active_positions: Dict[str, Dict] = {}
        self.trend_cache: Dict[str, TrendDirection] = {}
        
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        gains = [max(delta, 0) for delta in deltas]
        losses = [max(-delta, 0) for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def detect_trend(self, klines: List[Dict]) -> TrendDirection:
        """Detect trend direction using moving averages"""
        if len(klines) < self.config.TREND_PERIOD:
            return TrendDirection.SIDEWAYS
        
        closes = [float(kline['close']) for kline in klines]
        
        # Calculate short and long EMAs
        short_ema = self.calculate_ema(closes, 8)
        long_ema = self.calculate_ema(closes, 21)
        
        if short_ema is None or long_ema is None:
            return TrendDirection.SIDEWAYS
        
        # Determine trend
        if short_ema > long_ema * 1.001:  # 0.1% buffer to avoid noise
            return TrendDirection.UP
        elif short_ema < long_ema * 0.999:
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS
    
    def is_oversold_or_overbought(self, klines: List[Dict]) -> Tuple[bool, bool]:
        """Check if asset is oversold or overbought using RSI"""
        closes = [float(kline['close']) for kline in klines]
        rsi = self.calculate_rsi(closes, self.config.RSI_PERIOD)
        
        if rsi is None:
            return False, False
        
        oversold = rsi < self.config.RSI_OVERSOLD
        overbought = rsi > self.config.RSI_OVERBOUGHT
        
        return oversold, overbought
    
    def calculate_support_resistance(self, klines: List[Dict]) -> Tuple[float, float]:
        """Calculate basic support and resistance levels"""
        if len(klines) < 20:
            current_price = float(klines[-1]['close'])
            return current_price * 0.98, current_price * 1.02
        
        highs = [float(kline['high']) for kline in klines[-20:]]
        lows = [float(kline['low']) for kline in klines[-20:]]
        
        resistance = max(highs)
        support = min(lows)
        
        return support, resistance
    
    def analyze_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Analyze a symbol and generate trading signals"""
        try:
            # Get recent klines
            klines = self.binance_client.get_klines_sync(symbol, "1h", 100)
            if not klines:
                logger.warning(f"📊 {symbol}: No klines data available")
                return None
            
            current_price = float(klines[-1]['close'])
            trend = self.detect_trend(klines)
            oversold, overbought = self.is_oversold_or_overbought(klines)
            support, resistance = self.calculate_support_resistance(klines)
            
            # Cache trend
            self.trend_cache[symbol] = trend
            
            # Generate signals based on trend and RSI
            signal = self._generate_signal(
                symbol, current_price, trend, oversold, overbought, support, resistance
            )
            
            if signal:
                logger.info(f"🎯 {symbol}: Signal generated - {signal.signal_type.value} | Confidence={signal.confidence:.1%} | Reason: {signal.reason}")
            else:
                logger.debug(f"⏸️ {symbol}: No signal - conditions not met")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return None
    
    def _generate_signal(self, symbol: str, current_price: float, trend: TrendDirection, 
                        oversold: bool, overbought: bool, support: float, resistance: float) -> Optional[TradingSignal]:
        """Generate trading signal based on analysis"""
        
        # Check actual Binance positions first (most reliable)
        binance_positions = self.binance_client.get_open_positions_sync()
        has_binance_position = any(pos['symbol'] == symbol for pos in binance_positions)
        
        # Debug logging to see what's happening 
        logger.info(f"🔍 {symbol} Position Check: Binance has {len(binance_positions)} total positions")
        if binance_positions:
            symbols_list = [pos.get('symbol', 'unknown') for pos in binance_positions]
            logger.info(f"🔍 {symbol} Binance position symbols: {symbols_list}")
        logger.info(f"🔍 {symbol} Looking for {symbol} in Binance: {has_binance_position}")
        
        existing_position = None
        if has_binance_position:
            # Use actual Binance position data
            binance_pos = next(pos for pos in binance_positions if pos['symbol'] == symbol)
            existing_position = {
                'symbol': symbol,
                'quantity': abs(float(binance_pos.get('positionAmt', 0))),
                'entry_price': float(binance_pos.get('entryPrice', 0)),
                'side': 'LONG' if float(binance_pos.get('positionAmt', 0)) > 0 else 'SHORT'
            }
            logger.info(f"✅ {symbol} Found Binance position: {existing_position['side']} {existing_position['quantity']} at {existing_position['entry_price']}")
        
        # Do NOT fallback to local data - only use Binance as source of truth
        # Local data can be stale and cause false positives
        
        logger.info(f"📊 {symbol} Final position status: {'Has position' if existing_position else 'No position'}")
        
        # Log Binance positions summary (only once per cycle)
        if symbol == 'ETHUSDT':  # Log only once per scan cycle to avoid spam
            if len(binance_positions) > 0:
                symbols_with_positions = [pos['symbol'] for pos in binance_positions]
                logger.info(f"📊 Current Binance positions: {symbols_with_positions}")
            else:
                logger.info(f"📊 No open positions found on Binance")
        
        # Получаем RSI для детального логирования
        klines_for_rsi = self.binance_client.get_klines_sync(symbol, "1h", self.config.RSI_PERIOD + 10)
        current_rsi = self.calculate_rsi([float(k['close']) for k in klines_for_rsi], self.config.RSI_PERIOD) if klines_for_rsi else 0
        
        logger.info(f"🔍 {symbol} Signal Check: Trend={trend.value} | RSI={current_rsi:.1f} | "
                   f"Oversold={oversold}(<{self.config.RSI_OVERSOLD}) | Overbought={overbought}(>{self.config.RSI_OVERBOUGHT}) | "
                   f"HasPosition={existing_position is not None}")
        
        # BUY conditions: когда актив перепродан (oversold)
        if oversold and not existing_position:
            # Увеличиваем confidence если тренд тоже благоприятный
            confidence = 0.8 if trend == TrendDirection.UP else 0.6
            
            logger.info(f"✅ {symbol} BUY условие выполнено: RSI {current_rsi:.1f} < {self.config.RSI_OVERSOLD} (oversold)")
            stop_loss = current_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
            take_profit = current_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100)
            
            logger.info(f"✅ {symbol} BUY Signal: Oversold RSI | Trend={trend.value} | Confidence={confidence:.1%} | SL=${stop_loss:.4f} | TP=${take_profit:.4f}")
            
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Oversold RSI ({current_rsi:.1f}) in {trend.value.lower()} trend"
            )
        
        # SELL conditions: когда актив перекуплен (overbought)  
        elif overbought and not existing_position:
            # Увеличиваем confidence если тренд тоже благоприятный для short
            confidence = 0.8 if trend == TrendDirection.DOWN else 0.6
            
            logger.info(f"✅ {symbol} SELL условие выполнено: RSI {current_rsi:.1f} > {self.config.RSI_OVERBOUGHT} (overbought)")
            stop_loss = current_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
            take_profit = current_price * (1 - self.config.TAKE_PROFIT_PERCENT / 100)
            
            logger.info(f"✅ {symbol} SELL Signal: Overbought RSI | Trend={trend.value} | Confidence={confidence:.1%} | SL=${stop_loss:.4f} | TP=${take_profit:.4f}")
            
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Overbought RSI ({current_rsi:.1f}) in {trend.value.lower()} trend"
            )
        
        # Position averaging - add to winning positions on pullbacks
        elif existing_position and trend == TrendDirection.UP:
            entry_price = existing_position.get('entry_price', current_price)
            
            # Add to position if price pulled back but trend is still up
            if current_price < entry_price * 0.985 and oversold:  # 1.5% pullback
                return TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.ADD_POSITION,
                    confidence=0.6,
                    entry_price=current_price,
                    reason="Adding to position on pullback"
                )
        
        # Exit conditions for existing positions
        elif existing_position:
            entry_price = existing_position.get('entry_price', current_price)
            position_side = existing_position.get('side', 'LONG')
            
            # Get all open trades for this symbol to calculate average entry price
            open_trades = []
            if self.data_storage:
                all_trades = self.data_storage.get_trades()
                open_trades = [t for t in all_trades if t.get('symbol') == symbol and t.get('status') == 'open']
            else:
                # Fallback to active_positions if no data_storage
                open_trades = [t for t in self.active_positions.get(symbol, []) if t.get('status') == 'open']
            
            if open_trades:
                # Calculate weighted average entry price from BUY trades only
                buy_trades = [trade for trade in open_trades if trade.get('side') == 'BUY']
                if buy_trades:
                    total_value = sum(trade['price'] * trade['quantity'] for trade in buy_trades)
                    total_quantity = sum(trade['quantity'] for trade in buy_trades)
                    avg_entry_price = total_value / total_quantity if total_quantity > 0 else entry_price
                else:
                    avg_entry_price = entry_price
                
                # Get the oldest trade timestamp for minimum hold time check
                oldest_trade_time = min(datetime.fromisoformat(trade['timestamp']) for trade in open_trades)
                min_hold_time = timedelta(minutes=5)  # Minimum 5 minutes hold time
                
                # Only check exit conditions if minimum hold time has passed
                if datetime.now() - oldest_trade_time >= min_hold_time:
                    # Exit long position
                    if position_side == 'LONG':
                        # Add trading fees buffer to take profit (0.08% total fees = 0.04% buy + 0.04% sell)
                        fee_buffer = 0.0008  # 0.08%
                        take_profit_threshold = avg_entry_price * (1 + (self.config.TAKE_PROFIT_PERCENT / 100) + fee_buffer)
                        stop_loss_threshold = avg_entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
                        
                        logger.info(f"🔍 {symbol} Exit Check: Current={current_price:.4f} | AvgEntry={avg_entry_price:.4f} | TP≥{take_profit_threshold:.4f} | SL≤{stop_loss_threshold:.4f}")
                        
                        # Take profit or stop loss
                        if current_price >= take_profit_threshold:
                            logger.info(f"🎯 {symbol} TAKE PROFIT: {current_price:.4f} >= {take_profit_threshold:.4f} (avg entry: {avg_entry_price:.4f})")
                            return TradingSignal(
                                symbol=symbol,
                                signal_type=SignalType.SELL,
                                confidence=0.9,
                                entry_price=current_price,
                                reason=f"Take profit reached: {current_price:.4f} >= {take_profit_threshold:.4f}"
                            )
                        elif current_price <= stop_loss_threshold:
                            logger.info(f"🛑 {symbol} STOP LOSS: {current_price:.4f} <= {stop_loss_threshold:.4f} (avg entry: {avg_entry_price:.4f})")
                            return TradingSignal(
                                symbol=symbol,
                                signal_type=SignalType.SELL,
                                confidence=0.9,
                                entry_price=current_price,
                                reason=f"Stop loss triggered: {current_price:.4f} <= {stop_loss_threshold:.4f}"
                            )
                else:
                    time_remaining = min_hold_time - (datetime.now() - oldest_trade_time)
                    logger.debug(f"⏰ {symbol}: Minimum hold time not reached. Time remaining: {time_remaining}")
                    
            else:
                # Fallback to basic exit logic if no open trades found
                # Use strategy.active_positions to get timestamp if available
                position_from_cache = self.active_positions.get(symbol)
                position_timestamp = position_from_cache.get('timestamp') if position_from_cache else None
                
                if position_timestamp:
                    position_time = datetime.fromisoformat(position_timestamp) 
                    min_hold_time = timedelta(minutes=5)  # Same 5-minute minimum
                    
                    # Only exit if minimum hold time has passed
                    if datetime.now() - position_time >= min_hold_time:
                        if position_side == 'LONG':
                            fee_buffer = 0.0008
                            take_profit_threshold = entry_price * (1 + (self.config.TAKE_PROFIT_PERCENT / 100) + fee_buffer)
                            stop_loss_threshold = entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
                            
                            if current_price >= take_profit_threshold:
                                return TradingSignal(
                                    symbol=symbol,
                                    signal_type=SignalType.SELL,
                                    confidence=0.9,
                                    entry_price=current_price,
                                    reason="Take profit reached (fallback)"
                                )
                            elif current_price <= stop_loss_threshold:
                                return TradingSignal(
                                    symbol=symbol,
                                    signal_type=SignalType.SELL,
                                    confidence=0.9,
                                    entry_price=current_price,
                                    reason="Stop loss triggered (fallback)"
                                )
                        elif position_side == 'SHORT':
                            fee_buffer = 0.0008
                            take_profit_threshold = entry_price * (1 - (self.config.TAKE_PROFIT_PERCENT / 100) - fee_buffer)
                            stop_loss_threshold = entry_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
                            
                            if current_price <= take_profit_threshold:
                                return TradingSignal(
                                    symbol=symbol,
                                    signal_type=SignalType.SELL,
                                    confidence=0.9,
                                    entry_price=current_price,
                                    reason="Take profit reached (fallback - SHORT)"
                                )
                            elif current_price >= stop_loss_threshold:
                                return TradingSignal(
                                    symbol=symbol,
                                    signal_type=SignalType.SELL,
                                    confidence=0.9,
                                    entry_price=current_price,
                                    reason="Stop loss triggered (fallback - SHORT)"
                                )
                    else:
                        time_remaining = min_hold_time - (datetime.now() - position_time)
                        logger.debug(f"⏰ {symbol}: Fallback - minimum hold time not reached. Time remaining: {time_remaining}")
                else:
                    logger.warning(f"⚠️ {symbol}: No timestamp in position data for minimum hold time check")
        
        # Default: hold - log the reason
        if existing_position:
            logger.info(f"⏸️ {symbol}: HOLD - есть открытая позиция, новые сигналы не генерируем")
        else:
            logger.info(f"⏸️ {symbol}: HOLD - RSI в нейтральной зоне ({current_rsi:.1f}, нужно <{self.config.RSI_OVERSOLD} или >{self.config.RSI_OVERBOUGHT})")
        
        return TradingSignal(
            symbol=symbol,
            signal_type=SignalType.HOLD,
            confidence=0.5,
            entry_price=current_price,
            reason="No clear signal"
        )
    
    async def scan_opportunities(self, symbols: List[str]) -> List[TradingSignal]:
        """Scan multiple symbols for trading opportunities"""
        signals = []
        
        for symbol in symbols:
            try:
                signal = self.analyze_symbol(symbol)
                if signal and signal.signal_type != SignalType.HOLD:
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals
    
    def update_position(self, symbol: str, position_data: Dict):
        """Update active position data"""
        self.active_positions[symbol] = position_data
    
    def remove_position(self, symbol: str):
        """Remove position from active tracking"""
        if symbol in self.active_positions:
            del self.active_positions[symbol]
    
    def get_position_info(self, symbol: str) -> Optional[Dict]:
        """Get information about active position"""
        return self.active_positions.get(symbol)
    
    def get_trend_direction(self, symbol: str) -> TrendDirection:
        """Get cached trend direction"""
        return self.trend_cache.get(symbol, TrendDirection.SIDEWAYS)

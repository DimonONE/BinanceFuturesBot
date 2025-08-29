"""
Trading strategy implementation with trend following and position averaging
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
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
    
    def __init__(self, binance_client, config):
        self.binance_client = binance_client
        self.config = config
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
        
        # Check if we have an existing position
        existing_position = self.active_positions.get(symbol)
        
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
            
            # Exit long position
            if position_side == 'LONG':
                # Take profit or stop loss
                if current_price >= entry_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100):
                    return TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        confidence=0.9,
                        entry_price=current_price,
                        reason="Take profit reached"
                    )
                elif current_price <= entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100):
                    return TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        confidence=0.9,
                        entry_price=current_price,
                        reason="Stop loss triggered"
                    )
        
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

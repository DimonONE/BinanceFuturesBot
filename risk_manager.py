"""
Risk management module for trading operations
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    total_exposure: float
    available_balance: float
    max_position_size: float
    current_drawdown: float
    daily_pnl: float
    weekly_pnl: float

class RiskManager:
    """Risk management for automated trading"""
    
    def __init__(self, config, data_storage):
        self.config = config
        self.data_storage = data_storage
        self.initial_balance = 0.0
        self.peak_balance = 0.0
        self.daily_trades = 0
        self.max_daily_trades = 50
        
    async def initialize(self, initial_balance: float):
        """Initialize risk manager with starting balance"""
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        logger.info(f"Risk Manager initialized with balance: {initial_balance} USDT")
    
    def calculate_position_size(self, signal_confidence: float, available_balance: float, 
                              current_price: float) -> Tuple[float, bool]:
        """Calculate appropriate position size based on risk parameters"""
        try:
            # Base position size from config
            base_amount = self.config.DEFAULT_TRADE_AMOUNT
            
            # Adjust based on confidence
            confidence_multiplier = min(signal_confidence * 1.5, 1.0)
            adjusted_amount = base_amount * confidence_multiplier
            
            # Ensure we don't exceed available balance
            max_allowed = min(adjusted_amount, available_balance * 0.9)  # Keep 10% buffer
            
            # Ensure we don't exceed max position size
            final_amount = min(max_allowed, self.config.MAX_POSITION_SIZE)
            
            # Check minimum trade amount (usually 10 USDT for Binance)
            if final_amount < 10.0:
                return 0.0, False
            
            logger.info(f"Calculated position size: {final_amount} USDT (confidence: {signal_confidence})")
            return final_amount, True
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0, False
    
    def check_drawdown_limits(self, current_balance: float) -> bool:
        """Check if current drawdown exceeds maximum allowed"""
        try:
            # Update peak balance
            if current_balance > self.peak_balance:
                self.peak_balance = current_balance
            
            # Calculate current drawdown
            drawdown_percent = ((self.peak_balance - current_balance) / self.peak_balance) * 100
            
            if drawdown_percent > self.config.MAX_DRAWDOWN_PERCENT:
                logger.warning(f"Maximum drawdown exceeded: {drawdown_percent:.2f}% > {self.config.MAX_DRAWDOWN_PERCENT}%")
                return False
            
            logger.info(f"Current drawdown: {drawdown_percent:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"Error checking drawdown limits: {e}")
            return False
    
    def can_place_trade(self, symbol: str, trade_amount: float, current_balance: float) -> Tuple[bool, str]:
        """Check if a trade can be placed based on risk rules"""
        try:
            # Check minimum balance requirement
            if current_balance < 20.0:  # Minimum 20 USDT to trade
                return False, "Insufficient balance for trading"
            
            # Check if trade amount is within limits
            if trade_amount > current_balance * 0.9:
                return False, "Trade amount exceeds available balance"
            
            # Check drawdown limits
            if not self.check_drawdown_limits(current_balance):
                return False, "Maximum drawdown limit exceeded"
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                return False, "Maximum daily trades limit reached"
            
            # Check if we're not over-exposed to single symbol
            positions = self.data_storage.get_open_positions()
            symbol_exposure = sum(pos['usdt_value'] for pos in positions if pos['symbol'] == symbol)
            
            if symbol_exposure + trade_amount > self.config.MAX_POSITION_SIZE:
                return False, f"Would exceed maximum position size for {symbol}"
            
            # Check total exposure
            total_exposure = sum(pos['usdt_value'] for pos in positions)
            if total_exposure + trade_amount > current_balance * 0.8:  # Max 80% exposure
                return False, "Would exceed maximum total exposure"
            
            return True, "Trade approved"
            
        except Exception as e:
            logger.error(f"Error checking trade permissions: {e}")
            return False, f"Error in risk check: {str(e)}"
    
    def calculate_stop_loss_price(self, entry_price: float, side: str) -> float:
        """Calculate stop-loss price based on risk parameters"""
        try:
            if side.upper() == 'BUY' or side.upper() == 'LONG':
                # For long positions, stop loss is below entry price
                stop_loss = entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
            else:
                # For short positions, stop loss is above entry price
                stop_loss = entry_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
            
            return round(stop_loss, 6)
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return entry_price
    
    def calculate_take_profit_price(self, entry_price: float, side: str) -> float:
        """Calculate take-profit price based on risk parameters"""
        try:
            if side.upper() == 'BUY' or side.upper() == 'LONG':
                # For long positions, take profit is above entry price
                take_profit = entry_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100)
            else:
                # For short positions, take profit is below entry price
                take_profit = entry_price * (1 - self.config.TAKE_PROFIT_PERCENT / 100)
            
            return round(take_profit, 6)
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {e}")
            return entry_price
    
    def update_daily_trades(self):
        """Increment daily trade counter"""
        self.daily_trades += 1
        logger.info(f"Daily trades: {self.daily_trades}/{self.max_daily_trades}")
    
    def reset_daily_counters(self):
        """Reset daily counters (call this daily)"""
        self.daily_trades = 0
        logger.info("Daily trade counters reset")
    
    def get_risk_metrics(self, current_balance: float, positions: List[Dict]) -> RiskMetrics:
        """Get current risk metrics"""
        try:
            total_exposure = sum(pos['usdt_value'] for pos in positions)
            available_balance = current_balance - total_exposure
            max_position_size = self.config.MAX_POSITION_SIZE
            current_drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100 if self.peak_balance > 0 else 0
            
            # Calculate daily and weekly PnL
            trades = self.data_storage.get_recent_trades(days=1)
            daily_pnl = sum(trade['pnl'] for trade in trades if trade['status'] == 'closed')
            
            trades_weekly = self.data_storage.get_recent_trades(days=7)
            weekly_pnl = sum(trade['pnl'] for trade in trades_weekly if trade['status'] == 'closed')
            
            return RiskMetrics(
                total_exposure=total_exposure,
                available_balance=available_balance,
                max_position_size=max_position_size,
                current_drawdown=current_drawdown,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(0, current_balance, 0, 0, 0, 0)
    
    def should_reduce_risk(self, current_balance: float) -> bool:
        """Determine if we should reduce risk exposure"""
        try:
            # Reduce risk if drawdown is high
            drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100 if self.peak_balance > 0 else 0
            
            if drawdown > self.config.MAX_DRAWDOWN_PERCENT * 0.7:  # 70% of max drawdown
                return True
            
            # Reduce risk if balance is very low
            if current_balance < self.initial_balance * 0.5:  # Lost 50% of initial
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking risk reduction: {e}")
            return True  # Default to reducing risk on error

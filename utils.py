"""
Utility functions for the trading bot
"""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

def format_number(number: Union[int, float], decimals: int = 2) -> str:
    """Format number with thousands separators and specified decimal places"""
    try:
        if number is None:
            return "0.00"
        
        # Handle very small numbers
        if abs(number) < 0.01 and number != 0:
            return f"{number:.6f}".rstrip('0').rstrip('.')
        
        # Regular formatting
        return f"{number:,.{decimals}f}"
    except Exception:
        return "0.00"

def format_percentage(percentage: Union[int, float], decimals: int = 2) -> str:
    """Format percentage with specified decimal places"""
    try:
        if percentage is None:
            return "0.00"
        return f"{percentage:.{decimals}f}"
    except Exception:
        return "0.00"

def calculate_pnl(entry_price: float, current_price: float, quantity: float, side: str) -> float:
    """Calculate profit and loss for a position"""
    try:
        if side.upper() in ['BUY', 'LONG']:
            # Long position
            pnl = (current_price - entry_price) * quantity
        else:
            # Short position
            pnl = (entry_price - current_price) * quantity
        
        return pnl
    except Exception as e:
        logger.error(f"Error calculating PnL: {e}")
        return 0.0

def calculate_percentage_change(entry_price: float, current_price: float, side: str) -> float:
    """Calculate percentage change for a position"""
    try:
        if entry_price == 0:
            return 0.0
        
        if side.upper() in ['BUY', 'LONG']:
            # Long position
            percentage = ((current_price - entry_price) / entry_price) * 100
        else:
            # Short position
            percentage = ((entry_price - current_price) / entry_price) * 100
        
        return percentage
    except Exception as e:
        logger.error(f"Error calculating percentage change: {e}")
        return 0.0

def round_to_precision(value: float, precision: int) -> float:
    """Round value to specified decimal precision"""
    try:
        return round(value, precision)
    except Exception:
        return 0.0

def calculate_position_size_from_percentage(balance: float, percentage: float, price: float) -> float:
    """Calculate position size based on balance percentage"""
    try:
        usdt_amount = balance * (percentage / 100)
        quantity = usdt_amount / price
        return quantity
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.0

def validate_symbol(symbol: str) -> bool:
    """Validate if symbol format is correct"""
    try:
        if not symbol or len(symbol) < 6:
            return False
        
        # Check if it ends with USDT (for futures)
        if not symbol.upper().endswith('USDT'):
            return False
        
        # Check for valid characters
        if not symbol.replace('USDT', '').replace('usdt', '').isalpha():
            return False
        
        return True
    except Exception:
        return False

def calculate_stop_loss_price(entry_price: float, stop_loss_percent: float, side: str) -> float:
    """Calculate stop loss price"""
    try:
        if side.upper() in ['BUY', 'LONG']:
            return entry_price * (1 - stop_loss_percent / 100)
        else:
            return entry_price * (1 + stop_loss_percent / 100)
    except Exception as e:
        logger.error(f"Error calculating stop loss price: {e}")
        return entry_price

def calculate_take_profit_price(entry_price: float, take_profit_percent: float, side: str) -> float:
    """Calculate take profit price"""
    try:
        if side.upper() in ['BUY', 'LONG']:
            return entry_price * (1 + take_profit_percent / 100)
        else:
            return entry_price * (1 - take_profit_percent / 100)
    except Exception as e:
        logger.error(f"Error calculating take profit price: {e}")
        return entry_price

def calculate_risk_reward_ratio(entry_price: float, stop_loss: float, take_profit: float, side: str) -> float:
    """Calculate risk-reward ratio"""
    try:
        if side.upper() in ['BUY', 'LONG']:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
        else:
            risk = abs(stop_loss - entry_price)
            reward = abs(entry_price - take_profit)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    except Exception as e:
        logger.error(f"Error calculating risk-reward ratio: {e}")
        return 0.0

def is_market_hours() -> bool:
    """Check if market is in active hours (crypto is 24/7, so always True)"""
    return True

def time_since(timestamp: str) -> str:
    """Calculate time elapsed since timestamp"""
    try:
        dt = datetime.fromisoformat(timestamp)
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    except Exception:
        return "Unknown"

def calculate_drawdown(peak_balance: float, current_balance: float) -> float:
    """Calculate drawdown percentage"""
    try:
        if peak_balance == 0:
            return 0.0
        
        drawdown = ((peak_balance - current_balance) / peak_balance) * 100
        return max(0.0, drawdown)  # Drawdown cannot be negative
    except Exception as e:
        logger.error(f"Error calculating drawdown: {e}")
        return 0.0

def calculate_win_rate(winning_trades: int, total_trades: int) -> float:
    """Calculate win rate percentage"""
    try:
        if total_trades == 0:
            return 0.0
        return (winning_trades / total_trades) * 100
    except Exception as e:
        logger.error(f"Error calculating win rate: {e}")
        return 0.0

def calculate_average_pnl(trades: List[Dict]) -> float:
    """Calculate average PnL from trades"""
    try:
        if not trades:
            return 0.0
        
        total_pnl = sum(trade.get('pnl', 0) for trade in trades if trade.get('status') == 'closed')
        closed_trades = len([t for t in trades if t.get('status') == 'closed'])
        
        if closed_trades == 0:
            return 0.0
        
        return total_pnl / closed_trades
    except Exception as e:
        logger.error(f"Error calculating average PnL: {e}")
        return 0.0

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio"""
    try:
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize (assuming daily returns)
        annualized_return = mean_return * 365
        annualized_std = std_dev * math.sqrt(365)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        return sharpe
    except Exception as e:
        logger.error(f"Error calculating Sharpe ratio: {e}")
        return 0.0

def validate_trade_parameters(symbol: str, quantity: float, price: float) -> tuple[bool, str]:
    """Validate trade parameters"""
    try:
        # Check symbol
        if not validate_symbol(symbol):
            return False, "Invalid symbol format"
        
        # Check quantity
        if quantity <= 0:
            return False, "Quantity must be positive"
        
        # Check price
        if price <= 0:
            return False, "Price must be positive"
        
        # Check minimum trade value (usually 10 USDT for Binance)
        trade_value = quantity * price
        if trade_value < 10:
            return False, "Trade value too small (minimum 10 USDT)"
        
        return True, "Valid parameters"
    except Exception as e:
        logger.error(f"Error validating trade parameters: {e}")
        return False, f"Validation error: {str(e)}"

def get_risk_level(current_balance: float, initial_balance: float, max_drawdown: float) -> str:
    """Get risk level based on current state"""
    try:
        if initial_balance == 0:
            return "Unknown"
        
        current_drawdown = calculate_drawdown(initial_balance, current_balance)
        
        if current_drawdown < max_drawdown * 0.3:
            return "Low"
        elif current_drawdown < max_drawdown * 0.6:
            return "Medium"
        elif current_drawdown < max_drawdown * 0.9:
            return "High"
        else:
            return "Critical"
    except Exception as e:
        logger.error(f"Error calculating risk level: {e}")
        return "Unknown"

def format_timestamp(timestamp: Union[str, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to readable string"""
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return "Invalid timestamp"
        
        return dt.strftime(format_str)
    except Exception:
        return "Invalid timestamp"

def calculate_compound_return(initial_balance: float, final_balance: float, days: int) -> float:
    """Calculate compound annual growth rate (CAGR)"""
    try:
        if initial_balance <= 0 or final_balance <= 0 or days <= 0:
            return 0.0
        
        years = days / 365.25
        cagr = ((final_balance / initial_balance) ** (1 / years)) - 1
        return cagr * 100  # Return as percentage
    except Exception as e:
        logger.error(f"Error calculating compound return: {e}")
        return 0.0

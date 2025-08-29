"""
Configuration settings for the trading bot
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        # Telegram Bot Configuration
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.AUTHORIZED_USERS = self._parse_authorized_users()
        
        # Binance API Configuration
        self.BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
        self.BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
        self.BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        
        # Trading Configuration
        self.DEFAULT_TRADE_AMOUNT = float(os.getenv("DEFAULT_TRADE_AMOUNT", "15.0"))
        self.MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "100.0"))
        self.MAX_DRAWDOWN_PERCENT = float(os.getenv("MAX_DRAWDOWN_PERCENT", "20.0"))
        self.STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "3.0"))
        self.TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "6.0"))
        
        # Strategy Configuration
        self.TREND_PERIOD = int(os.getenv("TREND_PERIOD", "20"))
        self.RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
        self.RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
        self.RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
        
        # Data Storage Configuration
        self.DATA_FILE = os.getenv("DATA_FILE", "trading_data.json")
        self.BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", "3600"))  # 1 hour
        
        # WebSocket Configuration
        self.WEBSOCKET_TIMEOUT = int(os.getenv("WEBSOCKET_TIMEOUT", "30"))
        self.RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))
        
        # Default trading pairs
        self.DEFAULT_PAIRS = ["ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
        
    def _parse_authorized_users(self) -> list:
        """Parse authorized users from environment variable"""
        users_str = os.getenv("AUTHORIZED_USERS", "")
        if not users_str:
            return []
        
        try:
            return [int(user_id.strip()) for user_id in users_str.split(",") if user_id.strip()]
        except ValueError:
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""
        return {
            "default_trade_amount": self.DEFAULT_TRADE_AMOUNT,
            "max_position_size": self.MAX_POSITION_SIZE,
            "max_drawdown_percent": self.MAX_DRAWDOWN_PERCENT,
            "stop_loss_percent": self.STOP_LOSS_PERCENT,
            "take_profit_percent": self.TAKE_PROFIT_PERCENT,
            "trend_period": self.TREND_PERIOD,
            "rsi_period": self.RSI_PERIOD,
            "rsi_oversold": self.RSI_OVERSOLD,
            "rsi_overbought": self.RSI_OVERBOUGHT,
            "binance_testnet": self.BINANCE_TESTNET
        }

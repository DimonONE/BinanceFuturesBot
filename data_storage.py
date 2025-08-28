"""
Local JSON storage for trading data and user settings
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import shutil

logger = logging.getLogger(__name__)

class DataStorage:
    """Local JSON storage for trading bot data"""
    
    def __init__(self, data_file: str = "trading_data.json"):
        self.data_file = data_file
        self.backup_file = f"{data_file}.backup"
        self.data = {
            "user_settings": {},
            "trades": [],
            "positions": [],
            "balance_history": [],
            "bot_stats": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "start_date": datetime.now().isoformat()
            },
            "last_update": datetime.now().isoformat()
        }
        self._load_data()
    
    def _load_data(self):
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    loaded_data = json.load(f)
                    # Merge with default structure to ensure all keys exist
                    self._merge_dict(self.data, loaded_data)
                logger.info("Trading data loaded successfully")
            else:
                logger.info("No existing data file found, starting with default data")
                self._save_data()
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            # Try to load from backup
            self._load_from_backup()
    
    def _load_from_backup(self):
        """Load data from backup file"""
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r') as f:
                    loaded_data = json.load(f)
                    self._merge_dict(self.data, loaded_data)
                logger.warning("Data loaded from backup file")
            else:
                logger.error("No backup file available")
        except Exception as e:
            logger.error(f"Error loading backup data: {e}")
    
    def _merge_dict(self, base_dict: Dict, update_dict: Dict):
        """Recursively merge dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._merge_dict(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _save_data(self):
        """Save data to JSON file"""
        try:
            # Create backup before saving
            if os.path.exists(self.data_file):
                shutil.copy2(self.data_file, self.backup_file)
            
            # Update timestamp
            self.data["last_update"] = datetime.now().isoformat()
            
            # Save to file
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
            
            logger.debug("Data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def reload_data(self):
        """Reload data from JSON file"""
        self._load_data()
    
    def save_trade(self, trade_data: Dict):
        """Save a trade record"""
        try:
            trade_data["timestamp"] = datetime.now().isoformat()
            trade_data["id"] = len(self.data["trades"]) + 1
            
            self.data["trades"].append(trade_data)
            
            # Update statistics
            self.data["bot_stats"]["total_trades"] += 1
            if trade_data.get("status") == "closed":
                pnl = trade_data.get("pnl", 0.0)
                self.data["bot_stats"]["total_pnl"] += pnl
                
                if pnl > 0:
                    self.data["bot_stats"]["winning_trades"] += 1
                else:
                    self.data["bot_stats"]["losing_trades"] += 1
            
            self._save_data()
            logger.info(f"Trade saved: {trade_data['symbol']} - {trade_data['side']} - {trade_data.get('status', 'open')}")
            
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
    
    def update_trade(self, trade_id: int, updates: Dict):
        """Update an existing trade"""
        try:
            for trade in self.data["trades"]:
                if trade["id"] == trade_id:
                    trade.update(updates)
                    trade["last_updated"] = datetime.now().isoformat()
                    
                    # Update statistics if trade is closed
                    if updates.get("status") == "closed" and "pnl" in updates:
                        pnl = updates["pnl"]
                        self.data["bot_stats"]["total_pnl"] += pnl
                        
                        if pnl > 0:
                            self.data["bot_stats"]["winning_trades"] += 1
                        else:
                            self.data["bot_stats"]["losing_trades"] += 1
                    
                    self._save_data()
                    logger.info(f"Trade {trade_id} updated")
                    return True
            
            logger.warning(f"Trade {trade_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return False
    
    def get_trades(self, symbol: str = None, status: str = None, limit: int = None) -> List[Dict]:
        """Get trades with optional filtering"""
        try:
            trades = self.data["trades"]
            
            # Filter by symbol
            if symbol:
                trades = [t for t in trades if t.get("symbol") == symbol]
            
            # Filter by status
            if status:
                trades = [t for t in trades if t.get("status") == status]
            
            # Sort by timestamp (newest first)
            trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Apply limit
            if limit:
                trades = trades[:limit]
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_recent_trades(self, days: int = 7) -> List[Dict]:
        """Get trades from the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_trades = []
            
            for trade in self.data["trades"]:
                try:
                    trade_date = datetime.fromisoformat(trade["timestamp"])
                    if trade_date >= cutoff_date:
                        recent_trades.append(trade)
                except Exception:
                    continue
            
            return recent_trades
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    def save_position(self, position_data: Dict):
        """Save or update a position"""
        try:
            position_data["last_updated"] = datetime.now().isoformat()
            
            # Check if position already exists
            for i, pos in enumerate(self.data["positions"]):
                if pos["symbol"] == position_data["symbol"]:
                    self.data["positions"][i] = position_data
                    self._save_data()
                    logger.info(f"Position updated: {position_data['symbol']}")
                    return
            
            # Add new position
            self.data["positions"].append(position_data)
            self._save_data()
            logger.info(f"New position saved: {position_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Error saving position: {e}")
    
    def remove_position(self, symbol: str):
        """Remove a position"""
        try:
            self.data["positions"] = [pos for pos in self.data["positions"] if pos["symbol"] != symbol]
            self._save_data()
            logger.info(f"Position removed: {symbol}")
            
        except Exception as e:
            logger.error(f"Error removing position: {e}")
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            return [pos for pos in self.data["positions"] if pos.get("status") == "open"]
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get specific position"""
        try:
            for pos in self.data["positions"]:
                if pos["symbol"] == symbol:
                    return pos
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    def save_balance_snapshot(self, balance: float, unrealized_pnl: float = 0.0):
        """Save balance snapshot"""
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "balance": balance,
                "unrealized_pnl": unrealized_pnl,
                "total_value": balance + unrealized_pnl
            }
            
            self.data["balance_history"].append(snapshot)
            
            # Keep only last 1000 snapshots
            if len(self.data["balance_history"]) > 1000:
                self.data["balance_history"] = self.data["balance_history"][-1000:]
            
            self._save_data()
            
        except Exception as e:
            logger.error(f"Error saving balance snapshot: {e}")
    
    def get_balance_history(self, days: int = 30) -> List[Dict]:
        """Get balance history for the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            history = []
            
            for snapshot in self.data["balance_history"]:
                try:
                    snapshot_date = datetime.fromisoformat(snapshot["timestamp"])
                    if snapshot_date >= cutoff_date:
                        history.append(snapshot)
                except Exception:
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting balance history: {e}")
            return []
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        try:
            return self.data["user_settings"].get(str(user_id), {})
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return {}
    
    def save_user_settings(self, user_id: int, settings: Dict):
        """Save user settings"""
        try:
            self.data["user_settings"][str(user_id)] = settings
            self._save_data()
            logger.info(f"User settings saved for {user_id}")
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
    
    def get_bot_stats(self) -> Dict:
        """Get bot statistics"""
        try:
            return self.data["bot_stats"]
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {}
    
    def update_bot_stats(self, updates: Dict):
        """Update bot statistics"""
        try:
            self.data["bot_stats"].update(updates)
            self._save_data()
            logger.info("Bot statistics updated")
        except Exception as e:
            logger.error(f"Error updating bot stats: {e}")

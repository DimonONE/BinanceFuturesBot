# Overview

This is a complete Telegram-based cryptocurrency trading bot that integrates with Binance futures trading. The bot provides automated trading capabilities with advanced risk management, real-time price monitoring, and intuitive user interaction through Telegram commands. It implements a sophisticated trend-following strategy with smart position averaging and includes comprehensive risk controls to protect trading capital.

## ✅ Implementation Status

**Core Features Implemented:**
- ✅ Telegram bot interface with inline keyboards and callback handlers
- ✅ Binance futures API integration with WebSocket real-time data
- ✅ Advanced trend-following trading strategy with RSI indicators  
- ✅ Comprehensive risk management system with drawdown protection
- ✅ Local JSON-based data storage for trades and analytics
- ✅ Real-time balance and position monitoring
- ✅ Complete trade history and P&L analytics
- ✅ Configurable trading parameters and limits
- ✅ Smart position sizing based on signal confidence
- ✅ Automatic stop-loss and take-profit orders
- ✅ Multi-symbol monitoring and trading
- ✅ User authorization system
- ✅ Paper trading support via Binance testnet

**Bot Commands Available:**
- `/start` - Main menu with navigation buttons
- `/balance` - View USDT balance and portfolio value
- `/positions` - Display all open futures positions
- `/trades` - Show recent trade history (7 days)
- `/stats` - Trading performance statistics and metrics
- `/settings` - Configure bot parameters and view status
- `/help` - Comprehensive help and feature overview

**Risk Management Features:**
- ✅ Maximum drawdown protection (configurable %)
- ✅ Position size limits and balance allocation
- ✅ Daily trade limits to prevent overtrading
- ✅ Automatic stop-loss orders on all positions
- ✅ Smart position sizing based on signal confidence
- ✅ Balance verification before trade execution
- ✅ Emergency position closing capabilities

**Trading Strategy Features:**
- ✅ Trend detection using EMA crossovers (8/21 periods)
- ✅ RSI-based entry timing (oversold/overbought levels)
- ✅ Smart position averaging on pullbacks
- ✅ Multiple timeframe analysis support
- ✅ Signal confidence scoring for position sizing
- ✅ Support and resistance level calculation

## 🚀 Quick Start Guide

### 1. Setup Environment Variables
```bash
# Interactive setup (recommended)
python setup_env.py

# Or create .env manually from template
cp .env.example .env
# Edit .env with your API keys
```

### 2. Required API Keys
- **Telegram Bot Token**: Get from @BotFather in Telegram
- **Binance API Key/Secret**: Create in Binance API Management
- **Telegram User ID**: Get from @userinfobot (for authorization)

### 3. Start the Bot
```bash
python main.py
```

### 4. Bot Commands
Send `/start` to your bot in Telegram to access all features via interactive buttons.

### 5. Safety Recommendations
- ⚠️ **Start with testnet**: Set `BINANCE_TESTNET=true`
- 💰 **Use small amounts**: Begin with minimal trade sizes
- 📊 **Monitor actively**: Check positions and performance regularly
- 🛡️ **Set limits**: Configure appropriate stop-loss and position limits

# User Preferences

Preferred communication style: Simple, everyday language.
Interface language: Ukrainian (interface translated to українська мова)

# System Architecture

## Bot Architecture
The system follows a modular architecture with clear separation of concerns:

- **Main Entry Point**: `main.py` serves as the application launcher with logging configuration
- **Telegram Interface**: `telegram_bot.py` handles user interactions and command processing
- **Trading Engine**: Combines strategy execution, risk management, and order execution
- **Data Layer**: Local JSON-based storage for persistence without external database dependencies

## Trading Strategy Framework
The bot implements a trend-following strategy with technical analysis:

- **Signal Generation**: Uses moving averages, RSI, and trend detection algorithms
- **Position Management**: Supports both long and short positions with smart averaging
- **Multi-timeframe Analysis**: Analyzes different timeframes for signal confirmation
- **Confidence Scoring**: Assigns confidence levels to trading signals for position sizing

## Risk Management System
Comprehensive risk controls are built into the core architecture:

- **Position Sizing**: Dynamic calculation based on signal confidence and available balance
- **Drawdown Protection**: Monitors and limits maximum portfolio drawdown
- **Stop Loss/Take Profit**: Automatic risk management for all positions
- **Daily Trade Limits**: Prevents over-trading and excessive risk exposure

## Real-time Data Processing
WebSocket integration provides live market data:

- **Price Streaming**: Real-time price updates for monitored trading pairs
- **Event-driven Architecture**: Triggers strategy evaluation on price changes
- **Connection Management**: Automatic reconnection and error handling
- **Multiple Symbol Support**: Concurrent monitoring of multiple trading pairs

## Configuration Management
Environment-based configuration system:

- **Trading Parameters**: Configurable risk limits, strategy settings, and position sizes
- **API Credentials**: Secure handling of Binance API keys and secrets
- **User Authorization**: Telegram user access control via environment variables
- **Testnet Support**: Built-in support for paper trading on Binance testnet

## Data Persistence Design
Local JSON storage approach chosen for simplicity and portability:

- **No External Dependencies**: Eliminates need for database setup and maintenance
- **Backup System**: Automatic data backup and recovery mechanisms
- **Structured Storage**: Organized data format for trades, positions, and user settings
- **Performance Tracking**: Historical data for strategy analysis and optimization

# External Dependencies

## Binance Integration
- **Binance API**: Official Python library for futures trading operations
- **WebSocket Streams**: Real-time market data feeds
- **Testnet Support**: Paper trading environment for development and testing

## Telegram Bot Platform
- **Python Telegram Bot**: Async library for bot interface and user interactions
- **Webhook Support**: Scalable message handling architecture
- **Inline Keyboards**: Interactive command interface for trading operations

## Technical Analysis Libraries
- **NumPy**: Mathematical operations for technical indicators and signal processing
- **Native Calculations**: Custom implementations for moving averages, RSI, and trend analysis

## Configuration and Utilities
- **Environment Variables**: Secure configuration management via OS environment
- **JSON Storage**: Native Python JSON handling for data persistence
- **Asyncio**: Asynchronous programming for concurrent operations and real-time processing
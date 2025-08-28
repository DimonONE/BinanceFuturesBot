#!/usr/bin/env python3
"""
Main entry point for the Telegram Binance Trading Bot
"""

import asyncio
import logging
import sys
from telegram_bot import TradingBot
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the trading bot"""
    try:
        # Load configuration
        config = Config()
        
        # Validate required environment variables
        if not config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            sys.exit(1)
            
        if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
            logger.error("BINANCE_API_KEY and BINANCE_API_SECRET environment variables are required")
            sys.exit(1)
        
        # Create and start the trading bot
        bot = TradingBot(config)
        logger.info("Starting Telegram Binance Trading Bot...")
        
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

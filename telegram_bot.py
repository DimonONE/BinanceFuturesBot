"""
Telegram bot interface for the trading bot using telebot
"""

import logging
import asyncio
from typing import Dict, List, Optional
import telebot
from telebot import types
import threading
import time

from binance_client import BinanceClient
from trading_strategy import TrendFollowingStrategy, SignalType
from risk_manager import RiskManager
from data_storage import DataStorage
from websocket_handler import WebSocketHandler
from config import Config
from utils import format_number, format_percentage, calculate_pnl

logger = logging.getLogger(__name__)

class TradingBot:
    """Main Telegram bot for trading interface"""
    
    def __init__(self, config: Config):
        self.config = config
        self.bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
        
        # Initialize components
        self.data_storage = DataStorage(config.DATA_FILE)
        self.binance_client = BinanceClient(
            config.BINANCE_API_KEY,
            config.BINANCE_API_SECRET,
            config.BINANCE_TESTNET
        )
        self.risk_manager = RiskManager(config, self.data_storage)
        self.strategy = TrendFollowingStrategy(self.binance_client, config)
        self.websocket_handler = WebSocketHandler(self.binance_client)
        
        # Bot state
        self.is_trading_active = False
        self.monitoring_symbols = config.DEFAULT_PAIRS.copy()
        
        # Setup message handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup message and callback handlers"""
        
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            self.handle_start_command(message)
            
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            self.handle_help_command(message)
            
        @self.bot.message_handler(commands=['balance'])
        def balance_command(message):
            def run_async():
                asyncio.run(self.handle_balance_command(message))
            thread = threading.Thread(target=run_async)
            thread.start()
            
        @self.bot.message_handler(commands=['positions'])
        def positions_command(message):
            def run_async():
                asyncio.run(self.handle_positions_command(message))
            thread = threading.Thread(target=run_async)
            thread.start()
            
        @self.bot.message_handler(commands=['trades'])
        def trades_command(message):
            def run_async():
                asyncio.run(self.handle_trades_command(message))
            thread = threading.Thread(target=run_async)
            thread.start()
            
        @self.bot.message_handler(commands=['stats'])
        def stats_command(message):
            def run_async():
                asyncio.run(self.handle_stats_command(message))
            thread = threading.Thread(target=run_async)
            thread.start()
            
        @self.bot.message_handler(commands=['settings'])
        def settings_command(message):
            self.handle_settings_command(message)
            
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            def run_async():
                asyncio.run(self.handle_callback_query(call))
            thread = threading.Thread(target=run_async)
            thread.start()
    
    def _check_authorization(self, user_id: int) -> bool:
        """Check if user is authorized"""
        if not self.config.AUTHORIZED_USERS:
            return True  # If no authorized users set, allow all
        return user_id in self.config.AUTHORIZED_USERS
    
    def handle_start_command(self, message):
        """Handle /start command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        welcome_text = """
🚀 **Торговий бот Binance Futures**

Вітаємо у вашому автоматизованому торговому помічнику!

**Основні функції:**
• Автоматична торгівля ф'ючерсами з ризик-менеджментом
• Моніторинг балансу та позицій у реальному часі
• Вдосконалена трендслідна стратегія
• Повна історія торгів та аналітика
• Налаштовувані параметри ризику

**Швидкі команди:**
/balance - Переглянути баланс рахунку
/positions - Перевірити відкриті позиції
/trades - Недавня історія торгів
/stats - Статистика торгівлі
/settings - Налаштування бота

Використовуйте кнопки нижче для швидкої навігації:
        """
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            types.InlineKeyboardButton("📊 Позиції", callback_data="positions")
        )
        keyboard.add(
            types.InlineKeyboardButton("🔄 Почати торгівлю", callback_data="start_trading"),
            types.InlineKeyboardButton("⏸ Зупинити торгівлю", callback_data="stop_trading")
        )
        keyboard.add(
            types.InlineKeyboardButton("📈 Статистика", callback_data="stats"),
            types.InlineKeyboardButton("⚙️ Налаштування", callback_data="settings")
        )
        
        self.bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=keyboard)
    
    def handle_help_command(self, message):
        """Handle /help command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        help_text = """
📚 **Команди та функції бота**

**Торгові команди:**
/balance - Показати баланс USDT та інформацію про рахунок
/positions - Відобразити всі відкриті позиції
/trades - Показати недавню історію торгів
/stats - Статистика торгової діяльності
/settings - Налаштувати параметри бота

**Керування ботом:**
• Почати/Зупинити торгівлю - Контроль автоматичної торгівлі
• Ризик-менеджмент - Вбудовані стоп-лосс та тейк-профіт
• Розмір позиції - Розумне визначення розміру на основі ризику
• Вибір стратегії - Трендслідна з усередненням

**Ризик-менеджмент:**
• Захист від максимальної просадки
• Ордери стоп-лосс та тейк-профіт
• Обмеження розміру позиції
• Розподіл ризику на основі балансу

**Інформація про стратегію:**
Бот використовує трендслідну стратегію з розумним усередненням позицій:
1. Визначає тренди ринку за допомогою ковзних середніх
2. Відкриває позиції у напрямку тренду
3. Використовує RSI для визначення часу входу
4. Додає до прибуткових позицій на відкатах
5. Строгий ризик-менеджмент зі стопами

**Функції безпеки:**
• Доступний режим паперової торгівлі
• Максимальні щоденні ліміти торгів
• Комплексне логування та моніторинг
• Функціональність екстреної зупинки

Для підтримки, будь ласка, перевірте логи або зверніться до адміністратора.
        """
        
        self.bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
    
    async def handle_balance_command(self, message):
        """Handle /balance command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            # Get balance from Binance (using sync methods)
            usdt_balance = self.binance_client.get_usdt_balance_sync()
            all_balances = self.binance_client.get_account_balance_sync()
            
            # Get open positions
            positions = self.binance_client.get_open_positions_sync()
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            # Calculate total portfolio value
            total_value = usdt_balance + total_unrealized_pnl
            
            # Get risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics(usdt_balance, positions)
            
            balance_text = f"""
💰 **Баланс рахунку**

**Баланс USDT:** `{format_number(usdt_balance)} USDT`
**Нереалізований P&L:** `{format_number(total_unrealized_pnl)} USDT`
**Загальний портфель:** `{format_number(total_value)} USDT`

**Метрики ризику:**
• Доступний баланс: `{format_number(risk_metrics.available_balance)} USDT`
• Загальна експозиція: `{format_number(risk_metrics.total_exposure)} USDT`
• Поточна просадка: `{format_percentage(risk_metrics.current_drawdown)}%`
• Щоденний P&L: `{format_number(risk_metrics.daily_pnl)} USDT`

**Інші активи:**
            """
            
            for asset, balance in all_balances.items():
                if asset != 'USDT' and balance > 0:
                    balance_text += f"• {asset}: `{format_number(balance)}`\n"
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("🔄 Оновити", callback_data="balance"),
                types.InlineKeyboardButton("📊 Позиції", callback_data="positions")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, balance_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            self.bot.reply_to(message, "❌ Помилка отримання інформації про баланс.")
    
    async def handle_positions_command(self, message):
        """Handle /positions command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            positions = self.binance_client.get_open_positions_sync()
            
            if not positions:
                positions_text = "📊 **Відкриті позиції**\n\nВідкриті позиції не знайдено."
            else:
                positions_text = "📊 **Відкриті позиції**\n\n"
                
                for pos in positions:
                    symbol = pos['symbol']
                    side = pos['side']
                    size = abs(pos['position_amt'])
                    entry_price = pos['entry_price']
                    unrealized_pnl = pos['unrealized_pnl']
                    percentage = pos['percentage']
                    
                    # Get current price
                    current_price = self.binance_client.get_current_price_sync(symbol)
                    current_price_str = f"{format_number(current_price)}" if current_price else "N/A"
                    
                    pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
                    side_emoji = "🟢" if side == "LONG" else "🔴"
                    
                    positions_text += f"""
{side_emoji} **{symbol}** ({side})
• Size: `{format_number(size)}`
• Entry: `{format_number(entry_price)} USDT`
• Current: `{current_price_str} USDT`
• PnL: `{format_number(unrealized_pnl)} USDT` ({format_percentage(percentage)}%) {pnl_emoji}
                    """
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("🔄 Оновити", callback_data="positions"),
                types.InlineKeyboardButton("💰 Баланс", callback_data="balance")
            )
            keyboard.add(
                types.InlineKeyboardButton("🛑 Закрити все", callback_data="close_all_positions"),
                types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
            )
            
            self.bot.send_message(message.chat.id, positions_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            self.bot.reply_to(message, "❌ Error retrieving position information.")
    
    async def handle_trades_command(self, message):
        """Handle /trades command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            recent_trades = self.data_storage.get_recent_trades(days=7)
            
            if not recent_trades:
                trades_text = "📝 **Recent Trades (7 days)**\n\nNo trades found in the last 7 days."
            else:
                trades_text = "📝 **Recent Trades (7 days)**\n\n"
                
                for trade in recent_trades[:10]:  # Show last 10 trades
                    symbol = trade.get('symbol', 'N/A')
                    side = trade.get('side', 'N/A')
                    quantity = trade.get('quantity', 0)
                    price = trade.get('price', 0)
                    pnl = trade.get('pnl', 0)
                    status = trade.get('status', 'open')
                    timestamp = trade.get('timestamp', '')
                    
                    # Format timestamp
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = "N/A"
                    
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    status_emoji = "✅" if status == "closed" else "⏳"
                    
                    trades_text += f"""
{status_emoji} **{symbol}** - {side}
• Time: `{time_str}`
• Quantity: `{format_number(quantity)}`
• Price: `{format_number(price)} USDT`
• PnL: `{format_number(pnl)} USDT` {pnl_emoji}
• Status: `{status.upper()}`
                    """
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("📊 Statistics", callback_data="stats"),
                types.InlineKeyboardButton("💰 Баланс", callback_data="balance")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, trades_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            self.bot.reply_to(message, "❌ Error retrieving trade history.")
    
    async def handle_stats_command(self, message):
        """Handle /stats command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            bot_stats = self.data_storage.get_bot_stats()
            
            total_trades = bot_stats.get('total_trades', 0)
            winning_trades = bot_stats.get('winning_trades', 0)
            losing_trades = bot_stats.get('losing_trades', 0)
            total_pnl = bot_stats.get('total_pnl', 0.0)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Get recent performance
            recent_trades = self.data_storage.get_recent_trades(days=1)
            daily_trades = len(recent_trades)
            daily_pnl = sum(trade.get('pnl', 0) for trade in recent_trades if trade.get('status') == 'closed')
            
            weekly_trades = self.data_storage.get_recent_trades(days=7)
            weekly_pnl = sum(trade.get('pnl', 0) for trade in weekly_trades if trade.get('status') == 'closed')
            
            current_balance = self.binance_client.get_usdt_balance_sync()
            risk_reducing = self.risk_manager.should_reduce_risk(current_balance)
            
            stats_text = f"""
📈 **Trading Statistics**

**Overall Performance:**
• Total Trades: `{total_trades}`
• Winning Trades: `{winning_trades}`
• Losing Trades: `{losing_trades}`
• Win Rate: `{format_percentage(win_rate)}%`
• Total PnL: `{format_number(total_pnl)} USDT`

**Recent Performance:**
• Daily Trades: `{daily_trades}`
• Daily PnL: `{format_number(daily_pnl)} USDT`
• Weekly PnL: `{format_number(weekly_pnl)} USDT`

**Bot Status:**
• Trading Active: `{'✅ Yes' if self.is_trading_active else '❌ No'}`
• Monitoring Symbols: `{len(self.monitoring_symbols)}`
• Risk Level: `{'🟢 Low' if not risk_reducing else '🔴 High'}`
            """
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("📝 Recent Trades", callback_data="trades"),
                types.InlineKeyboardButton("📊 Позиції", callback_data="positions")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            self.bot.reply_to(message, "❌ Error retrieving statistics.")
    
    def handle_settings_command(self, message):
        """Handle /settings command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            settings_text = f"""
        ⚙️ **Налаштування Бота**

        **Ризик-менеджмент:**
        • Сума за замовчуванням: `{format_number(self.config.DEFAULT_TRADE_AMOUNT)} USDT`
        • Максимальний розмір позиції: `{format_number(self.config.MAX_POSITION_SIZE)} USDT`
        • Стоп-лосс: `{self.config.STOP_LOSS_PERCENT}%`
        • Тейк-профіт: `{self.config.TAKE_PROFIT_PERCENT}%`
        • Максимальна просадка: `{self.config.MAX_DRAWDOWN_PERCENT}%`

        **Параметри Стратегії:**
        • Період Тренду: `{self.config.TREND_PERIOD}`
        • Період RSI: `{self.config.RSI_PERIOD}`
        • RSI Перепроданий: `{self.config.RSI_OVERSOLD}`
        • RSI Перекуплений: `{self.config.RSI_OVERBOUGHT}`

        **Система:**
        • Режим Тестнет: `{'✅ Так' if self.config.BINANCE_TESTNET else '❌ Ні'}`
        • Моніторинг Парами: `{len(self.monitoring_symbols)}`
        • Авто Торгівля: `{'✅ Активна' if self.is_trading_active else '❌ Неактивна'}`
            """
            
            # Додаємо кнопки
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("🔧 Змінити Налаштування", callback_data="modify_settings"),
                types.InlineKeyboardButton("📋 Переглянути Пари", callback_data="view_pairs")
            )
            keyboard.add(
                types.InlineKeyboardButton("🔄 Почати торгівлю", callback_data="start_trading"),
                types.InlineKeyboardButton("⏸ Зупинити торгівлю", callback_data="stop_trading")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, settings_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            self.bot.reply_to(message, "❌ Error retrieving settings.")
    
    async def handle_callback_query(self, call):
        """Handle callback queries from inline keyboards"""
        user_id = call.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.answer_callback_query(call.id, "❌ You are not authorized to use this bot.")
            return
        
        try:
            if call.data == "balance":
                await self.handle_balance_callback(call)
            elif call.data == "positions":
                await self.handle_positions_callback(call)
            elif call.data == "trades":
                await self.handle_trades_callback(call)
            elif call.data == "stats":
                await self.handle_stats_callback(call)
            elif call.data == "settings":
                await self.handle_settings_callback(call)
            elif call.data == "start_trading":
                await self.handle_start_trading_callback(call)
            elif call.data == "stop_trading":
                await self.handle_stop_trading_callback(call)
            elif call.data == "close_all_positions":
                await self.handle_close_all_positions_callback(call)
            elif call.data == "main_menu":
                await self.handle_main_menu_callback(call)
            else:
                self.bot.answer_callback_query(call.id, "Unknown command.")
                
        except Exception as e:
            logger.error(f"Error handling callback {call.data}: {e}")
            self.bot.answer_callback_query(call.id, "❌ Error processing request.")
    
    async def handle_balance_callback(self, call):
        """Handle balance callback"""
        # Create a message object from callback query
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = type('', (), {'id': chat_id})()
                self.from_user = from_user
        
        fake_message = FakeMessage(call.message.chat.id, call.from_user)
        await self.handle_balance_command(fake_message)
        self.bot.answer_callback_query(call.id)
    
    async def handle_positions_callback(self, call):
        """Handle positions callback"""
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = type('', (), {'id': chat_id})()
                self.from_user = from_user
        
        fake_message = FakeMessage(call.message.chat.id, call.from_user)
        await self.handle_positions_command(fake_message)
        self.bot.answer_callback_query(call.id)
    
    async def handle_trades_callback(self, call):
        """Handle trades callback"""
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = type('', (), {'id': chat_id})()
                self.from_user = from_user
        
        fake_message = FakeMessage(call.message.chat.id, call.from_user)
        await self.handle_trades_command(fake_message)
        self.bot.answer_callback_query(call.id)
    
    async def handle_stats_callback(self, call):
        """Handle stats callback"""
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = type('', (), {'id': chat_id})()
                self.from_user = from_user
        
        fake_message = FakeMessage(call.message.chat.id, call.from_user)
        await self.handle_stats_command(fake_message)
        self.bot.answer_callback_query(call.id)
    
    async def handle_settings_callback(self, call):
        """Handle settings callback"""
        class FakeMessage:
            def __init__(self, chat_id, from_user):
                self.chat = type('', (), {'id': chat_id})()
                self.from_user = from_user
        
        fake_message = FakeMessage(call.message.chat.id, call.from_user)
        self.handle_settings_command(fake_message)
        self.bot.answer_callback_query(call.id)
    
    async def handle_start_trading_callback(self, call):
        """Handle start trading callback"""
        if self.is_trading_active:
            self.bot.edit_message_text("✅ Торгівля вже активна!", call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
            return
        
        self.is_trading_active = True
        
        # Start the trading loop in a separate thread
        threading.Thread(target=self._start_trading_loop, daemon=True).start()
        
        self.bot.edit_message_text("🚀 Automated trading started!\n\nThe bot will now monitor markets and execute trades based on the strategy.", 
                                  call.message.chat.id, call.message.message_id)
        self.bot.answer_callback_query(call.id)
    
    async def handle_stop_trading_callback(self, call):
        """Handle stop trading callback"""
        if not self.is_trading_active:
            self.bot.edit_message_text("⏸ Trading is already stopped!", call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
            return
        
        self.is_trading_active = False
        self.bot.edit_message_text("⏸ Automated trading stopped!\n\nThe bot will no longer execute new trades, but existing positions remain open.", 
                                  call.message.chat.id, call.message.message_id)
        self.bot.answer_callback_query(call.id)
    
    async def handle_close_all_positions_callback(self, call):
        """Handle close all positions callback"""
        try:
            positions = await self.binance_client.get_open_positions()
            
            if not positions:
                self.bot.edit_message_text("No open positions to close.", call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id)
                return
            
            closed_count = 0
            for position in positions:
                symbol = position['symbol']
                side = 'SELL' if position['side'] == 'LONG' else 'BUY'
                quantity = abs(position['position_amt'])
                
                # Place market order to close position
                order = await self.binance_client.place_market_order(symbol, side, quantity)
                if order:
                    closed_count += 1
                    
                    # Save trade record
                    current_price = await self.binance_client.get_current_price(symbol)
                    pnl = calculate_pnl(position['entry_price'], current_price, quantity, position['side'])
                    
                    trade_data = {
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'price': current_price,
                        'pnl': pnl,
                        'status': 'closed',
                        'order_id': order.get('orderId', ''),
                        'type': 'market_close'
                    }
                    
                    self.data_storage.save_trade(trade_data)
            
            message = f"✅ Closed {closed_count} out of {len(positions)} positions."
            self.bot.edit_message_text(message, call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            self.bot.edit_message_text("❌ Error closing positions.", call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
    
    async def handle_main_menu_callback(self, call):
        """Handle main menu callback"""
        # Recreate the main menu
        welcome_text = """
🚀 **Binance Futures Trading Bot**

Welcome back! Use the buttons below for quick navigation:
        """
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            types.InlineKeyboardButton("📊 Позиції", callback_data="positions")
        )
        keyboard.add(
            types.InlineKeyboardButton("🔄 Почати торгівлю", callback_data="start_trading"),
            types.InlineKeyboardButton("⏸ Зупинити торгівлю", callback_data="stop_trading")
        )
        keyboard.add(
            types.InlineKeyboardButton("📈 Статистика", callback_data="stats"),
            types.InlineKeyboardButton("⚙️ Налаштування", callback_data="settings")
        )
        
        self.bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id, 
                                  parse_mode='Markdown', reply_markup=keyboard)
        self.bot.answer_callback_query(call.id)
    
    def _start_trading_loop(self):
        """Start the trading loop in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.trading_loop())
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")
        
        while self.is_trading_active:
            try:
                # Scan for opportunities
                signals = await self.strategy.scan_opportunities(self.monitoring_symbols)
                
                for signal in signals:
                    if not self.is_trading_active:
                        break
                    
                    await self.process_trading_signal(signal)
                
                # Wait before next scan
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
        
        logger.info("Trading loop stopped")
    
    async def process_trading_signal(self, signal):
        """Process a trading signal"""
        try:
            symbol = signal.symbol
            current_balance = self.binance_client.get_usdt_balance_sync()
            
            # Check risk management
            position_size, can_trade = self.risk_manager.calculate_position_size(
                signal.confidence, current_balance, signal.entry_price
            )
            
            if not can_trade:
                logger.info(f"Trade rejected by risk management for {symbol}")
                return
            
            can_place, reason = self.risk_manager.can_place_trade(symbol, position_size, current_balance)
            if not can_place:
                logger.info(f"Trade blocked: {reason}")
                return
            
            # Calculate quantity from USDT amount
            quantity = await self.binance_client.calculate_quantity_from_usdt(symbol, position_size)
            if not quantity:
                logger.error(f"Could not calculate quantity for {symbol}")
                return
            
            # Place the order
            side = 'BUY' if signal.signal_type == SignalType.BUY else 'SELL'
            order = await self.binance_client.place_market_order(symbol, side, quantity)
            
            if order:
                # Save trade record
                trade_data = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': signal.entry_price,
                    'pnl': 0.0,
                    'status': 'open',
                    'order_id': order.get('orderId', ''),
                    'type': 'market',
                    'signal_confidence': signal.confidence,
                    'reason': signal.reason
                }
                
                self.data_storage.save_trade(trade_data)
                self.risk_manager.update_daily_trades()
                
                logger.info(f"Trade executed: {side} {quantity} {symbol} at {signal.entry_price}")
                
                # Place stop-loss order
                if signal.stop_loss:
                    stop_side = 'SELL' if side == 'BUY' else 'BUY'
                    await self.binance_client.place_stop_loss_order(symbol, stop_side, quantity, signal.stop_loss)
            
        except Exception as e:
            logger.error(f"Error processing signal for {signal.symbol}: {e}")
    
    async def start(self):
        """Start the Telegram bot"""
        try:
            # Initialize Binance client
            if not await self.binance_client.initialize():
                raise Exception("Failed to initialize Binance client")
            
            # Initialize risk manager
            initial_balance = await self.binance_client.get_usdt_balance()
            await self.risk_manager.initialize(initial_balance)
            
            # Start WebSocket handler
            await self.websocket_handler.start(self.monitoring_symbols)
            
            # Start bot polling in a separate thread
            logger.info("Starting Telegram bot...")
            polling_thread = threading.Thread(target=self.bot.polling, kwargs={'none_stop': True}, daemon=True)
            polling_thread.start()
            
            # Keep the main thread alive
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
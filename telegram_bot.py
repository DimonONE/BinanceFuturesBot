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
        
        # Cache for symbols and user sessions
        self._cached_symbols = None
        self._user_search_sessions = {}  # user_id -> {"symbols": [...], "search_query": ""}
        
        # Setup message handlers
        self._setup_handlers()
        self._setup_search_handler()
        
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
• Автоматичні стоп-лосси на всі позиції
• Обмеження розміру позицій
• Захист від переторгівлі

**Безпека:**
⚠️ Рекомендовано почати з тестової мережі
💰 Використовуйте невеликі суми для початку
📊 Регулярно моніторте позиції

Використовуйте кнопки для швидкої навігації або команди напряму.
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
• Розмір: `{format_number(size)}`
• Вхід: `{format_number(entry_price)} USDT`
• Поточна: `{current_price_str} USDT`
• P&L: `{format_number(unrealized_pnl)} USDT` ({format_percentage(percentage)}%) {pnl_emoji}
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
            self.bot.reply_to(message, "❌ Помилка отримання інформації про позиції.")
    
    async def handle_trades_command(self, message):
        """Handle /trades command"""
        user_id = message.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.reply_to(message, "❌ Ви не авторизовані для використання цього бота.")
            return
        
        try:
            recent_trades = self.data_storage.get_recent_trades(days=7)
            
            if not recent_trades:
                trades_text = "📝 **Останні торги (7 днів)**\n\nТоргів за останні 7 днів не знайдено."
            else:
                trades_text = "📝 **Останні торги (7 днів)**\n\n"
                
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
• Час: `{time_str}`
• Кількість: `{format_number(quantity)}`
• Ціна: `{format_number(price)} USDT`
• P&L: `{format_number(pnl)} USDT` {pnl_emoji}
• Статус: `{status.upper()}`
                    """
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                types.InlineKeyboardButton("💰 Баланс", callback_data="balance")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, trades_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            self.bot.reply_to(message, "❌ Помилка отримання історії торгів.")
    
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
📈 **Статистика торгівлі**

**Загальна продуктивність:**
• Всього торгів: `{total_trades}`
• Прибуткові торги: `{winning_trades}`
• Збиткові торги: `{losing_trades}`
• Відсоток виграшів: `{format_percentage(win_rate)}%`
• Загальний P&L: `{format_number(total_pnl)} USDT`

**Недавня продуктивність:**
• Торгів за день: `{daily_trades}`
• Денний P&L: `{format_number(daily_pnl)} USDT`
• Тижневий P&L: `{format_number(weekly_pnl)} USDT`

**Статус бота:**
• Торгівля активна: `{'✅ Так' if self.is_trading_active else '❌ Ні'}`
• Відстежувані символи: `{len(self.monitoring_symbols)}`
• Рівень ризику: `{'🟢 Низький' if not risk_reducing else '🔴 Високий'}`
            """
            
            # Add buttons
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("📝 Останні торги", callback_data="trades"),
                types.InlineKeyboardButton("📊 Позиції", callback_data="positions")
            )
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            self.bot.reply_to(message, "❌ Помилка отримання статистики.")
    
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
            self.bot.reply_to(message, "❌ Помилка отримання налаштувань.")
    
    async def handle_callback_query(self, call):
        """Handle callback queries from inline keyboards"""
        user_id = call.from_user.id
        
        if not self._check_authorization(user_id):
            self.bot.answer_callback_query(call.id, "❌ Ви не авторизовані для використання цього бота.")
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
            elif call.data == "view_pairs":
                await self.handle_view_pairs_callback(call)
            elif call.data.startswith("pairs_page_"):
                await self.handle_pairs_page_callback(call)
            elif call.data.startswith("toggle_pair_"):
                await self.handle_toggle_pair_callback(call)
            elif call.data == "search_pairs":
                await self.handle_search_pairs_callback(call)
            elif call.data == "clear_search":
                await self.handle_clear_search_callback(call)
            elif call.data == "modify_settings":
                await self.handle_modify_settings_callback(call)
            elif call.data == "apply_pairs":
                await self.handle_apply_pairs_callback(call)
            elif call.data == "reset_pairs":
                await self.handle_reset_pairs_callback(call)
            else:
                self.bot.answer_callback_query(call.id, "❌ Невідома команда.")
                
        except Exception as e:
            logger.error(f"Error handling callback {call.data}: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка обробки запиту.")
    
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
        
        # Enhanced notification about trading start
        start_msg = f"""🚀 **Автоматична торгівля запущена!**

**Пари для моніторингу:** {len(self.monitoring_symbols)}
• {', '.join(self.monitoring_symbols[:3])}{'...' if len(self.monitoring_symbols) > 3 else ''}

🔍 Пошук торгових сигналів кожну хвилину...
📊 Отримаєте повідомлення про кожну операцію
"""
        
        self.bot.edit_message_text(start_msg, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        self.bot.answer_callback_query(call.id, "🚀 Торгівля запущена!")
    
    async def handle_stop_trading_callback(self, call):
        """Handle stop trading callback"""
        if not self.is_trading_active:
            self.bot.edit_message_text("⏸ Торгівля вже зупинена!", call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
            return
        
        self.is_trading_active = False
        self.bot.edit_message_text("⏸ Автоматична торгівля зупинена!\n\nБот більше не виконуватиме нові торги, але існуючі позиції залишаються відкритими.", 
                                  call.message.chat.id, call.message.message_id)
        self.bot.answer_callback_query(call.id)
    
    async def handle_close_all_positions_callback(self, call):
        """Handle close all positions callback"""
        try:
            positions = await self.binance_client.get_open_positions()
            
            if not positions:
                self.bot.edit_message_text("Немає відкритих позицій для закриття.", call.message.chat.id, call.message.message_id)
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
                    if current_price:
                        pnl = calculate_pnl(position['entry_price'], current_price, quantity, position['side'])
                    else:
                        pnl = 0.0
                    
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
            
            message = f"✅ Закрито {closed_count} з {len(positions)} позицій."
            self.bot.edit_message_text(message, call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            self.bot.edit_message_text("❌ Помилка закриття позицій.", call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id)
    
    async def handle_main_menu_callback(self, call):
        """Handle main menu callback"""
        # Recreate the main menu
        welcome_text = """
🚀 **Торговий бот Binance Futures**

З поверненням! Використовуйте кнопки нижче для швидкої навігації:
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
                logger.info(f"🔍 Scanning {len(self.monitoring_symbols)} symbols for trading opportunities...")
                
                # Scan for opportunities
                signals = await self.strategy.scan_opportunities(self.monitoring_symbols)
                
                if signals:
                    logger.info(f"🎯 Found {len(signals)} trading signals: {[f'{s.symbol}-{s.signal_type.value}' for s in signals[:3]]}")
                    for signal in signals:
                        logger.info(f"  📈 {signal.symbol}: {signal.signal_type.value} (confidence: {signal.confidence:.1%}) - {signal.reason}")
                else:
                    logger.info(f"⏸️ No trading signals found across {len(self.monitoring_symbols)} symbols")
                
                for signal in signals:
                    if not self.is_trading_active:
                        break
                    
                    logger.info(f"🔄 Processing signal for {signal.symbol}...")
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
            logger.info(f"💼 Processing {signal.signal_type.value} signal for {symbol}")
            
            current_balance = self.binance_client.get_usdt_balance_sync()
            logger.info(f"💰 Current balance: ${current_balance:.2f} USDT")
            
            # Check risk management
            position_size, can_trade = self.risk_manager.calculate_position_size(
                signal.confidence, current_balance, signal.entry_price
            )
            
            if not can_trade:
                logger.warning(f"❌ Trade rejected by position size calculation for {symbol}")
                return
            
            can_place, reason = self.risk_manager.can_place_trade(symbol, position_size, current_balance)
            if not can_place:
                logger.warning(f"❌ Trade blocked for {symbol}: {reason}")
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
                
                # Send notification to user about trade
                try:
                    trade_msg = f"""🎯 **Торгова операція виконана!**

**Пара:** {symbol}
**Операція:** {'Покупка' if side == 'BUY' else 'Продаж'}
**Кількість:** {quantity}
**Ціна:** {signal.entry_price} USDT
**Довіра сигналу:** {signal.confidence:.1%}
**Причина:** {signal.reason}
"""
                    # Send to authorized user
                    user_ids = [self.config.TELEGRAM_USER_ID] if hasattr(self.config, 'TELEGRAM_USER_ID') else []
                    if hasattr(self.config, 'TELEGRAM_USER_IDS'):
                        user_ids.extend(self.config.TELEGRAM_USER_IDS)
                    
                    for user_id in user_ids:
                        try:
                            self.bot.send_message(user_id, trade_msg, parse_mode='Markdown')
                        except Exception as e:
                            logger.error(f"Failed to send trade notification to {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error sending trade notification: {e}")
                
                # Place stop-loss order
                if signal.stop_loss:
                    stop_side = 'SELL' if side == 'BUY' else 'BUY'
                    stop_order = await self.binance_client.place_stop_loss_order(symbol, stop_side, quantity, signal.stop_loss)
                    if stop_order:
                        logger.info(f"Stop-loss placed: {stop_side} {quantity} {symbol} at {signal.stop_loss}")
                    else:
                        logger.error(f"Failed to place stop-loss for {symbol}")
            else:
                logger.error(f"Failed to execute trade for {symbol}: Order placement failed")
            
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
            
            # Load user settings and update monitoring symbols
            user_data = self.data_storage.data.get("user_settings", {})
            if user_data:
                # Get the first user's settings (since we have only one user configured)
                first_user_id = next(iter(user_data.keys()))
                user_settings = user_data[first_user_id]
                selected_pairs = user_settings.get('selected_pairs', self.config.DEFAULT_PAIRS)
                if selected_pairs and selected_pairs != self.monitoring_symbols:
                    logger.info(f"Loading user trading pairs: {self.monitoring_symbols} -> {selected_pairs}")
                    self.monitoring_symbols = selected_pairs.copy()
            
            # Start WebSocket handler
            self.websocket_handler.start(self.monitoring_symbols)
            
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
    
    def _get_cached_symbols(self):
        """Get cached symbols, fetch if not cached"""
        if self._cached_symbols is None:
            logger.info("Fetching exchange symbols for the first time...")
            self._cached_symbols = self.binance_client.get_exchange_symbols_sync()
            if not self._cached_symbols:
                self._cached_symbols = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "AVAXUSDT", "MATICUSDT"]
            logger.info(f"Cached {len(self._cached_symbols)} symbols")
        return self._cached_symbols

    def _init_user_session(self, user_id: int):
        """Initialize user session for pairs selection"""
        if user_id not in self._user_search_sessions:
            self._user_search_sessions[user_id] = {
                "symbols": self._get_cached_symbols().copy(),
                "search_query": ""
            }

    async def handle_view_pairs_callback(self, call):
        """Handle view pairs callback"""
        self._init_user_session(call.from_user.id)
        await self.show_pairs_page(call, 0)
        
    async def show_pairs_page(self, call, page: int):
        """Show trading pairs with pagination"""
        try:
            user_id = call.from_user.id
            self._init_user_session(user_id)
            
            # Get user settings
            user_settings = self.data_storage.get_user_settings(user_id)
            selected_pairs = user_settings.get('selected_pairs', self.config.DEFAULT_PAIRS.copy())
            
            # Get filtered symbols from user session
            session = self._user_search_sessions[user_id]
            filtered_symbols = session["symbols"]
            search_query = session["search_query"]
            
            # Pagination settings
            pairs_per_page = 5
            total_pages = (len(filtered_symbols) + pairs_per_page - 1) // pairs_per_page
            start_idx = page * pairs_per_page
            end_idx = min(start_idx + pairs_per_page, len(filtered_symbols))
            page_symbols = filtered_symbols[start_idx:end_idx]
            
            # Build header text with selected pairs info
            search_info = f" (Пошук: '{search_query}')" if search_query else ""
            
            # Show selected pairs (up to 10, then ...)
            if selected_pairs:
                if len(selected_pairs) <= 10:
                    selected_display = ', '.join(selected_pairs)
                else:
                    selected_display = ', '.join(selected_pairs[:10]) + '...'
                selected_info = f"**Вибрані пари ({len(selected_pairs)}):** {selected_display}"
            else:
                selected_info = "**Вибрані пари:** Немає"
            
            pairs_text = f"""📋 **Торгові Пари** (Сторінка {page + 1}/{total_pages}){search_info}

{selected_info}
**Знайдено пар:** {len(filtered_symbols)}
"""
            
            # Create inline keyboard with pairs
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            
            for symbol in page_symbols:
                is_selected = symbol in selected_pairs
                status_emoji = "✅" if is_selected else "❌"
                try:
                    current_price = self.binance_client.get_current_price_sync(symbol)
                    price_str = f" - {format_number(current_price)} USDT" if current_price else ""
                except:
                    price_str = ""
                
                button_text = f"{status_emoji} {symbol}{price_str}"
                keyboard.add(types.InlineKeyboardButton(button_text, callback_data=f"toggle_pair_{symbol}"))
            
            # Navigation buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(types.InlineKeyboardButton("⬅️ Попередня", callback_data=f"pairs_page_{page-1}"))
            if page < total_pages - 1:
                nav_buttons.append(types.InlineKeyboardButton("Наступна ➡️", callback_data=f"pairs_page_{page+1}"))
            
            if nav_buttons:
                keyboard.row(*nav_buttons)
            
            # Search and control buttons
            search_buttons = []
            if search_query:
                search_buttons.append(types.InlineKeyboardButton("❌ Очистити пошук", callback_data="clear_search"))
            search_buttons.append(types.InlineKeyboardButton("🔍 Пошук", callback_data="search_pairs"))
            keyboard.row(*search_buttons)
            
            # Control buttons
            keyboard.add(
                types.InlineKeyboardButton("💾 Зберегти та Застосувати", callback_data="apply_pairs"),
                types.InlineKeyboardButton("🔄 Скинути до стандартних", callback_data="reset_pairs")
            )
            keyboard.add(types.InlineKeyboardButton("⚙️ Назад до Налаштувань", callback_data="settings"))
            
            # Clear session when going back to settings
            if user_id in self._user_search_sessions:
                del self._user_search_sessions[user_id]
            
            # Update message
            self.bot.edit_message_text(pairs_text, call.message.chat.id, call.message.message_id, 
                                      parse_mode='Markdown', reply_markup=keyboard)
            
            # Only answer callback query if it's a real callback (has valid id)
            if hasattr(call, 'id') and call.id != "fake_search_call":
                self.bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error showing pairs page: {str(e)}")
            # Only answer callback query if it's a real callback (has valid id)
            if hasattr(call, 'id') and call.id != "fake_search_call":
                self.bot.answer_callback_query(call.id, "❌ Помилка відображення пар.")
    
    async def handle_modify_settings_callback(self, call):
        """Handle modify settings callback"""
        try:
            settings_text = f"""
🔧 **Налаштування Торгівлі**

**Поточні параметри:**
• Розмір позиції: {format_number(self.config.DEFAULT_TRADE_AMOUNT)} USDT
• Максимальна позиція: {format_number(self.config.MAX_POSITION_SIZE)} USDT
• Максимальна просадка: {self.config.MAX_DRAWDOWN_PERCENT}%
• Стоп-лосс: {self.config.STOP_LOSS_PERCENT}%
• Тейк-профіт: {self.config.TAKE_PROFIT_PERCENT}%

**Стратегія:**
• Період тренду: {self.config.TREND_PERIOD}
• Період RSI: {self.config.RSI_PERIOD}
• RSI перепроданість: {self.config.RSI_OVERSOLD}
• RSI перекупленість: {self.config.RSI_OVERBOUGHT}

**Мережа:** {"🟢 Testnet" if self.config.BINANCE_TESTNET else "🔴 Mainnet"}
**Статус торгівлі:** {"🟢 Активна" if self.is_trading_active else "⏸ Зупинена"}

ℹ️ Для зміни параметрів відредагуйте файл .env та перезапустіть бота
"""
            
            keyboard = types.InlineKeyboardMarkup()
            if self.is_trading_active:
                keyboard.add(types.InlineKeyboardButton("⏸ Зупинити торгівлю", callback_data="stop_trading"))
            else:
                keyboard.add(types.InlineKeyboardButton("🔄 Почати торгівлю", callback_data="start_trading"))
            
            keyboard.add(types.InlineKeyboardButton("📋 Переглянути пари", callback_data="view_pairs"))
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.edit_message_text(settings_text, call.message.chat.id, call.message.message_id,
                                      parse_mode='Markdown', reply_markup=keyboard)
            self.bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error showing modify settings: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка при завантаженні налаштувань.")
    
    async def handle_pairs_page_callback(self, call):
        """Handle pagination for pairs"""
        try:
            page = int(call.data.split("_")[-1])
            await self.show_pairs_page(call, page)
        except Exception as e:
            logger.error(f"Error handling pairs page: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка навігації.")
    
    async def handle_toggle_pair_callback(self, call):
        """Handle toggling a trading pair"""
        try:
            symbol = call.data.replace("toggle_pair_", "")
            user_id = call.from_user.id
            
            # Initialize session if needed
            self._init_user_session(user_id)
            
            # Get current user settings
            user_settings = self.data_storage.get_user_settings(user_id)
            selected_pairs = user_settings.get('selected_pairs', self.config.DEFAULT_PAIRS.copy())
            
            # Toggle the pair
            if symbol in selected_pairs:
                selected_pairs.remove(symbol)
                action = "вимкнено"
            else:
                selected_pairs.append(symbol)
                action = "увімкнено"
            
            # Save updated settings
            user_settings['selected_pairs'] = selected_pairs
            self.data_storage.save_user_settings(user_id, user_settings)
            
            # Show feedback and refresh page
            self.bot.answer_callback_query(call.id, f"✅ {symbol} {action}")
            
            # Refresh current page - try to determine current page from filtered symbols
            if user_id in self._user_search_sessions:
                session = self._user_search_sessions[user_id]
                try:
                    symbol_index = session["symbols"].index(symbol) if symbol in session["symbols"] else 0
                    current_page = symbol_index // 5  # 5 pairs per page
                except Exception:
                    current_page = 0
            else:
                current_page = 0
            
            await self.show_pairs_page(call, current_page)
            
        except Exception as e:
            logger.error(f"Error toggling pair {symbol if 'symbol' in locals() else 'unknown'}: {str(e)}")
            self.bot.answer_callback_query(call.id, "❌ Помилка зміни пари.")
    
    async def handle_apply_pairs_callback(self, call):
        """Apply selected pairs to monitoring"""
        try:
            # Get user settings
            user_settings = self.data_storage.get_user_settings(call.from_user.id)
            selected_pairs = user_settings.get('selected_pairs', self.config.DEFAULT_PAIRS.copy())
            
            if not selected_pairs:
                self.bot.answer_callback_query(call.id, "❌ Виберіть хоча б одну пару!")
                return
            
            # Update monitoring symbols
            old_symbols = self.monitoring_symbols.copy()
            self.monitoring_symbols = selected_pairs.copy()
            
            # Restart WebSocket handler with new symbols
            self.websocket_handler.stop()
            await asyncio.sleep(1)  # Give it time to stop
            self.websocket_handler.start(self.monitoring_symbols)
            
            # Show success message
            success_text = f"""✅ **Налаштування Застосовано**
            
**Пари для моніторингу оновлено:**
• Кількість пар: {len(selected_pairs)}
• Активні пари: {', '.join(selected_pairs[:5])}{'...' if len(selected_pairs) > 5 else ''}

🔄 WebSocket підключення перезапущено з новими парами.
"""
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("⚙️ Назад до Налаштувань", callback_data="settings"))
            keyboard.add(types.InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
            
            self.bot.edit_message_text(success_text, call.message.chat.id, call.message.message_id,
                                      parse_mode='Markdown', reply_markup=keyboard)
            self.bot.answer_callback_query(call.id, f"✅ Застосовано {len(selected_pairs)} пар!")
            
            logger.info(f"Monitoring symbols updated: {old_symbols} -> {self.monitoring_symbols}")
            
        except Exception as e:
            logger.error(f"Error applying pairs: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка застосування налаштувань.")
    
    async def handle_reset_pairs_callback(self, call):
        """Reset pairs to default"""
        try:
            # Get user settings
            user_settings = self.data_storage.get_user_settings(call.from_user.id)
            user_settings['selected_pairs'] = self.config.DEFAULT_PAIRS.copy()
            self.data_storage.save_user_settings(call.from_user.id, user_settings)
            
            self.bot.answer_callback_query(call.id, "🔄 Скинуто до стандартних пар!")
            
            # Refresh current page
            await self.show_pairs_page(call, 0)
            
        except Exception as e:
            logger.error(f"Error resetting pairs: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка скидання налаштувань.")
    
    def update_monitoring_symbols_from_user(self, user_id: int):
        """Update monitoring symbols from user settings"""
        try:
            user_settings = self.data_storage.get_user_settings(user_id)
            selected_pairs = user_settings.get('selected_pairs', self.config.DEFAULT_PAIRS.copy())
            
            if selected_pairs and selected_pairs != self.monitoring_symbols:
                old_symbols = self.monitoring_symbols.copy()
                self.monitoring_symbols = selected_pairs.copy()
                
                # Restart WebSocket handler
                self.websocket_handler.stop()
                self.websocket_handler.start(self.monitoring_symbols)
                
                logger.info(f"Monitoring symbols updated from user settings: {old_symbols} -> {self.monitoring_symbols}")
                
        except Exception as e:
            logger.error(f"Error updating monitoring symbols: {e}")
    
    async def handle_search_pairs_callback(self, call):
        """Handle search pairs callback"""
        try:
            user_id = call.from_user.id
            
            # Initialize user session if needed
            self._init_user_session(user_id)
            
            # Send a message asking for search query
            search_text = """🔍 **Пошук Торгових Пар**

Введіть назву криптовалюти або частину назви для пошуку:

**Приклади:**
• BTC (знайде BTCUSDT)
• ETH (знайде ETHUSDT) 
• DOG (знайде DOGEUSDT)
• 1INCH (знайде 1INCHUSDT)

Відправте повідомлення з пошуковим запитом або натисніть "Скасувати" для відміни."""
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("❌ Скасувати", callback_data="view_pairs"))
            
            # Send new message for search input
            sent_msg = self.bot.send_message(call.message.chat.id, search_text, parse_mode='Markdown', reply_markup=keyboard)
            
            # Store message info for cleanup
            if user_id not in self._user_search_sessions:
                self._init_user_session(user_id)
                
            self._user_search_sessions[user_id]["search_message_id"] = sent_msg.message_id
            self._user_search_sessions[user_id]["original_message_id"] = call.message.message_id
            
            self.bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"Error in search pairs callback: {str(e)}")
            self.bot.answer_callback_query(call.id, "❌ Помилка пошуку.")
    
    async def handle_clear_search_callback(self, call):
        """Handle clear search callback"""
        try:
            user_id = call.from_user.id
            self._init_user_session(user_id)
            
            # Reset search
            session = self._user_search_sessions[user_id]
            session["search_query"] = ""
            session["symbols"] = self._get_cached_symbols().copy()
            
            self.bot.answer_callback_query(call.id, "🔍 Пошук очищено")
            await self.show_pairs_page(call, 0)
            
        except Exception as e:
            logger.error(f"Error clearing search: {e}")
            self.bot.answer_callback_query(call.id, "❌ Помилка очищення пошуку.")
    
    def _setup_search_handler(self):
        """Setup search message handler"""
        @self.bot.message_handler(func=lambda message: (
            hasattr(message, 'text') and message.text and 
            message.from_user.id in self._user_search_sessions and 
            self._user_search_sessions[message.from_user.id].get("search_message_id") is not None
        ))
        def handle_search_input(message):
            def run_async():
                asyncio.run(self.process_search_input(message))
            thread = threading.Thread(target=run_async)
            thread.start()
    
    async def process_search_input(self, message):
        """Process search input from user"""
        try:
            user_id = message.from_user.id
            if user_id not in self._user_search_sessions:
                logger.warning(f"User {user_id} not in search sessions")
                return
                
            session = self._user_search_sessions[user_id]
            if not hasattr(message, 'text') or not message.text:
                logger.warning(f"No text in message from user {user_id}")
                return
                
            search_query = message.text.strip().upper()
            logger.info(f"Processing search query: '{search_query}' from user {user_id}")
            
            # Filter symbols based on search
            all_symbols = self._get_cached_symbols()
            if search_query:
                filtered_symbols = [symbol for symbol in all_symbols if search_query in symbol]
            else:
                filtered_symbols = all_symbols.copy()
            
            # Update session
            session["search_query"] = search_query
            session["symbols"] = filtered_symbols
            
            # Delete search message and user input
            try:
                search_msg_id = session.get("search_message_id")
                if search_msg_id:
                    self.bot.delete_message(message.chat.id, search_msg_id)
                self.bot.delete_message(message.chat.id, message.message_id)
            except Exception as delete_error:
                logger.warning(f"Could not delete messages: {delete_error}")
            
            # Update original pairs message
            original_msg_id = session.get("original_message_id")
            if original_msg_id:
                # Create fake call object for show_pairs_page
                class FakeCall:
                    def __init__(self, chat_id, message_id, user_id):
                        self.message = type('', (), {'chat': type('', (), {'id': chat_id})(), 'message_id': message_id})()
                        self.from_user = type('', (), {'id': user_id})()
                        self.id = "fake_search_call"  # Add missing id attribute
                
                fake_call = FakeCall(message.chat.id, original_msg_id, user_id)
                await self.show_pairs_page(fake_call, 0)
                
                # Send feedback
                feedback_msg = f"🔍 Знайдено {len(filtered_symbols)} пар за запитом '{search_query}'" if search_query else "🔍 Показано всі пари"
                try:
                    feedback = self.bot.send_message(message.chat.id, feedback_msg)
                    
                    # Delete feedback after 2 seconds in a separate thread
                    def delete_feedback():
                        import time
                        time.sleep(2)
                        try:
                            self.bot.delete_message(message.chat.id, feedback.message_id)
                        except:
                            pass
                    
                    import threading
                    threading.Thread(target=delete_feedback, daemon=True).start()
                except Exception as feedback_error:
                    logger.warning(f"Could not send feedback: {feedback_error}")
            
            # Clean up session search state
            session.pop("search_message_id", None)
            session.pop("original_message_id", None)
            
        except Exception as e:
            logger.error(f"Error processing search input: {str(e)}")
            try:
                self.bot.send_message(message.chat.id, "❌ Помилка обробки пошуку.")
            except:
                pass
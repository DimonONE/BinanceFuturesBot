#!/usr/bin/env python3
"""
Environment setup helper for the Telegram Trading Bot
This script helps you configure the required environment variables
"""

import os

def setup_environment():
    """Interactive setup for environment variables"""
    print("🚀 Настройка Telegram Trading Bot")
    print("=" * 50)
    
    # Environment variables to configure
    env_vars = {
        'TELEGRAM_BOT_TOKEN': {
            'description': 'Токен Telegram бота (получите у @BotFather)',
            'required': True,
            'example': '1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        },
        'BINANCE_API_KEY': {
            'description': 'API ключ Binance Futures',
            'required': True,
            'example': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        },
        'BINANCE_API_SECRET': {
            'description': 'API секрет Binance Futures',
            'required': True,
            'example': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        },
        'BINANCE_TESTNET': {
            'description': 'Использовать тестовую сеть Binance (true/false)',
            'required': False,
            'default': 'true',
            'example': 'true'
        },
        'AUTHORIZED_USERS': {
            'description': 'ID пользователей Telegram через запятую (оставьте пустым для доступа всем)',
            'required': False,
            'example': '123456789,987654321'
        },
        'DEFAULT_TRADE_AMOUNT': {
            'description': 'Размер позиции по умолчанию в USDT',
            'required': False,
            'default': '10.0',
            'example': '10.0'
        },
        'MAX_POSITION_SIZE': {
            'description': 'Максимальный размер позиции в USDT',
            'required': False,
            'default': '100.0',
            'example': '100.0'
        },
        'MAX_DRAWDOWN_PERCENT': {
            'description': 'Максимальная просадка в процентах',
            'required': False,
            'default': '20.0',
            'example': '20.0'
        },
        'STOP_LOSS_PERCENT': {
            'description': 'Стоп-лосс в процентах',
            'required': False,
            'default': '3.0',
            'example': '3.0'
        },
        'TAKE_PROFIT_PERCENT': {
            'description': 'Тейк-профит в процентах',
            'required': False,
            'default': '6.0',
            'example': '6.0'
        }
    }
    
    env_content = []
    
    print("Введите значения для переменных окружения:")
    print("(Нажмите Enter для использования значения по умолчанию, если оно есть)\n")
    
    for var_name, config in env_vars.items():
        print(f"📋 {var_name}")
        print(f"   Описание: {config['description']}")
        if 'example' in config:
            print(f"   Пример: {config['example']}")
        if 'default' in config:
            print(f"   По умолчанию: {config['default']}")
        
        while True:
            value = input(f"   Введите значение: ").strip()
            
            # Use default if available and no value entered
            if not value and 'default' in config:
                value = config['default']
                print(f"   Используется значение по умолчанию: {value}")
            
            # Check if required field is empty
            if config['required'] and not value:
                print("   ❌ Это поле обязательно для заполнения!")
                continue
            
            # Add to env file if value provided
            if value:
                env_content.append(f"{var_name}={value}")
            
            break
        
        print()
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write('\n'.join(env_content))
    
    print("✅ Файл .env создан успешно!")
    print("\n🔧 Дополнительные настройки:")
    print("- Для изменения торговых пар отредактируйте config.py")
    print("- Для изменения стратегии отредактируйте trading_strategy.py")
    print("\n🚀 Запуск бота:")
    print("   python main.py")
    print("\n⚠️  ВАЖНО:")
    print("- Сначала протестируйте на testnet (BINANCE_TESTNET=true)")
    print("- Используйте небольшие суммы для начала")
    print("- Регулярно мониторьте работу бота")
    print("- Убедитесь, что у вас достаточно средств для торговли")

def create_sample_env():
    """Create a sample .env file"""
    sample_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# Authorization (comma-separated Telegram user IDs, leave empty for public access)
AUTHORIZED_USERS=

# Trading Configuration
DEFAULT_TRADE_AMOUNT=10.0
MAX_POSITION_SIZE=100.0
MAX_DRAWDOWN_PERCENT=20.0
STOP_LOSS_PERCENT=3.0
TAKE_PROFIT_PERCENT=6.0

# Strategy Configuration
TREND_PERIOD=20
RSI_PERIOD=14
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
"""
    
    with open('.env.example', 'w') as f:
        f.write(sample_content)
    
    print("✅ Файл .env.example создан!")
    print("Скопируйте его в .env и заполните своими данными:")
    print("   cp .env.example .env")

def show_instructions():
    """Show setup instructions"""
    print("""
🚀 Инструкция по настройке Telegram Trading Bot

1. СОЗДАНИЕ TELEGRAM БОТА:
   - Найдите @BotFather в Telegram
   - Отправьте команду /newbot
   - Следуйте инструкциям для создания бота
   - Сохраните полученный токен

2. НАСТРОЙКА BINANCE API:
   - Войдите в аккаунт Binance
   - Перейдите в API Management
   - Создайте новый API ключ
   - Включите торговлю фьючерсами
   - Сохраните API Key и Secret Key
   - ⚠️  РЕКОМЕНДУЕТСЯ: сначала тестируйте на Testnet

3. ПОЛУЧЕНИЕ TELEGRAM USER ID:
   - Найдите @userinfobot в Telegram
   - Отправьте команду /start
   - Скопируйте ваш User ID

4. НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:
   - Запустите: python setup_env.py
   - Или создайте файл .env вручную

5. ЗАПУСК БОТА:
   - python main.py

📋 ТРЕБОВАНИЯ:
- Python 3.8+
- Аккаунт Binance с включенными фьючерсами
- Telegram бот токен
- Минимум 50 USDT на аккаунте для тестирования

⚠️  ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ:
- Торговля криптовалютами связана с высокими рисками
- Начинайте с небольших сумм
- Всегда тестируйте на testnet перед реальной торговлей
- Регулярно мониторьте работу бота
- Используйте стоп-лоссы для ограничения убытков
""")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "sample":
            create_sample_env()
        elif sys.argv[1] == "help":
            show_instructions()
        else:
            print("Доступные команды:")
            print("  python setup_env.py       - Интерактивная настройка")
            print("  python setup_env.py sample - Создать пример .env файла")
            print("  python setup_env.py help  - Показать подробную инструкцию")
    else:
        setup_environment()
"""
Скрипт для проверки конфигурации без запуска бота.

Проверяет, что все необходимые переменные окружения настроены корректно.
"""

import sys
from pathlib import Path


## Проверка конфигурации приложения
def check_configuration() -> bool:
    """
    Проверяет корректность конфигурации приложения.
    
    Проверяет наличие .env файла и корректность загрузки настроек.
    Выводит подробную информацию о каждой проверке.
    
    :return: True если конфигурация корректна, False в противном случае
    """
    print("🔍 Проверка конфигурации...\n")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Файл .env не найден")
        print("💡 Создайте файл .env на основе .env.example:")
        print("   cp .env.example .env")
        return False
    
    print("✅ Файл .env найден")
    
    try:
        from config import get_settings
        print("✅ Модуль config импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта модуля config: {e}")
        return False
    
    try:
        settings = get_settings()
        print("✅ Настройки загружены")
    except Exception as e:
        print(f"❌ Ошибка загрузки настроек: {e}")
        print("\n💡 Проверьте правильность переменных в .env файле")
        return False
    
    print("\n📋 Проверка переменных окружения:\n")
    
    checks = [
        ("BOT_TOKEN", settings.bot_token, "Токен Telegram бота"),
        ("LOG_LEVEL", settings.log_level, "Уровень логирования"),
        ("LOG_FILE", settings.log_file, "Путь к файлу логов"),
        ("MAX_TRANSACTION_AMOUNT", settings.max_transaction_amount, "Макс. сумма транзакции"),
    ]
    
    all_ok = True
    
    for var_name, value, description in checks:
        if value and str(value) != "your_telegram_bot_token_here":
            print(f"✅ {var_name}: {description}")
            if var_name == "BOT_TOKEN":
                masked = value[:8] + "..." + value[-4:]
                print(f"   Значение: {masked}")
            else:
                print(f"   Значение: {value}")
        else:
            print(f"⚠️  {var_name}: {description}")
            print(f"   Не настроено или используется значение по умолчанию")
            if var_name == "BOT_TOKEN":
                all_ok = False
    
    print("\n" + "="*50)
    
    if all_ok:
        print("✅ Конфигурация корректна! Можно запускать бота:")
        print("   python main.py")
    else:
        print("❌ Требуется настройка конфигурации")
        print("\n💡 Обязательно укажите BOT_TOKEN в .env файле")
        print("   Получить токен: https://t.me/BotFather")
    
    return all_ok


if __name__ == "__main__":
    try:
        success = check_configuration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1)


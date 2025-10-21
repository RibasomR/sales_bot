"""
Скрипт для проверки OpenRouter API подключения.
"""

import asyncio
import sys

from config import get_settings
from src.services.openrouter_service import parse_transaction_text


async def check_openrouter():
    """
    Проверяет подключение к OpenRouter API.
    """
    print("🔍 Проверка OpenRouter API...\n")
    
    settings = get_settings()
    
    if not settings.openrouter_api_key:
        print("❌ OpenRouter API ключ не найден в .env")
        print("\n💡 Добавьте OPENROUTER_API_KEY в .env файл")
        print("   Получить ключ: https://openrouter.ai/keys")
        print("   Инструкция: docs/openrouter_setup.md")
        return False
    
    print(f"✅ API ключ найден: {settings.openrouter_api_key[:15]}...")
    
    # Тест парсинга
    test_text = "Потратил 500 рублей на продукты"
    print(f"\n🧪 Тестирую парсинг: '{test_text}'")
    
    try:
        result = await parse_transaction_text(test_text)
        print("\n✅ OpenRouter API работает!")
        print(f"📊 Результат парсинга:")
        print(f"   • Тип: {result['type']}")
        print(f"   • Сумма: {result['amount']} ₽")
        print(f"   • Категория: {result.get('category', 'Не определена')}")
        print(f"   • Описание: {result.get('description', 'Нет')}")
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при обращении к OpenRouter API:")
        print(f"   {str(e)}")
        print("\n💡 Возможные причины:")
        print("   1. Неверный API ключ - проверьте OPENROUTER_API_KEY в .env")
        print("   2. Нет интернет соединения")
        print("   3. OpenRouter API временно недоступен")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(check_openrouter())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⛔ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1)


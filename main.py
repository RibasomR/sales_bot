"""
Главный модуль Telegram-бота для учета доходов и расходов.

Инициализирует бота, регистрирует handlers и запускает polling.
"""

import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from loguru import logger

from config import get_settings
from src.utils.logger import setup_logging
from src.handlers import common, voice, transactions, view, categories, export, settings
from src.models import init_db, close_db
from src.services.database import initialize_default_categories
from src.middlewares import (
    RateLimitMiddleware,
    ErrorHandlerMiddleware,
)


## Инициализация и запуск бота
async def main() -> None:
    """
    Главная функция запуска бота.
    
    Выполняет следующие действия:
    1. Настраивает систему логирования
    2. Загружает конфигурацию из переменных окружения
    3. Инициализирует подключение к базе данных
    4. Создает предустановленные категории
    5. Инициализирует Redis для rate limiting
    6. Создает экземпляры Bot и Dispatcher
    7. Регистрирует middlewares
    8. Регистрирует все handlers
    9. Запускает polling для получения обновлений
    
    :return: None
    :raises Exception: При критических ошибках инициализации или работы бота
    """
    setup_logging()
    logger.info("🚀 Запуск бота...")
    
    try:
        config_settings = get_settings()
        logger.info("✅ Конфигурация загружена успешно")
    except Exception as e:
        logger.critical(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.critical(f"❌ Ошибка инициализации БД: {e}")
        sys.exit(1)
    
    try:
        await initialize_default_categories()
        logger.info("✅ Предустановленные категории проверены")
    except Exception as e:
        logger.error(f"⚠️ Ошибка инициализации категорий: {e}")
    
    bot = Bot(
        token=config_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    ## Устанавливаем меню команд бота
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="add", description="➕ Добавить транзакцию"),
        BotCommand(command="transactions", description="📝 Все транзакции"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="categories", description="🏷️ Управление категориями"),
        BotCommand(command="export", description="📤 Экспорт данных"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="help", description="❓ Справка"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Меню команд установлено")
    
    dp = Dispatcher()
    
    ## Регистрируем middlewares
    dp.message.middleware(RateLimitMiddleware(max_requests=20, time_window=60))
    dp.callback_query.middleware(RateLimitMiddleware(max_requests=20, time_window=60))
    logger.info("✅ Rate limiting активирован (in-memory)")
    
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    logger.info("✅ Error handler активирован")
    
    dp.include_router(view.router)
    dp.include_router(settings.router)
    dp.include_router(categories.router)
    dp.include_router(export.router)
    dp.include_router(voice.router)
    dp.include_router(transactions.router)
    dp.include_router(common.router)
    logger.info("✅ Handlers зарегистрированы")
    
    try:
        logger.info("🔄 Начинаю polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при работе бота: {e}")
        raise
    finally:
        await bot.session.close()
        await close_db()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Необработанная ошибка: {e}")
        sys.exit(1)


"""
Модуль настройки логирования.

Настраивает систему логирования с использованием loguru для всего приложения.
"""

import sys
from pathlib import Path
from loguru import logger
from config import get_settings


## Настройка логирования приложения
def setup_logging() -> None:
    """
    Настраивает систему логирования для приложения.
    
    Создает два обработчика логов:
    1. Консольный вывод с цветным форматированием
    2. Файловый вывод с ротацией по размеру
    
    Логи записываются в файл, указанный в настройках (settings.log_file).
    Размер файла ограничен 10 МБ, после чего создается новый файл.
    Хранятся последние 5 файлов логов.
    
    :return: None
    
    Example:
        >>> setup_logging()
        >>> logger.info("Application started")
    """
    settings = get_settings()
    
    logger.remove()
    
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention=5,
        compression="zip",
        encoding="utf-8",
    )
    
    logger.info(f"Логирование настроено. Уровень: {settings.log_level}")


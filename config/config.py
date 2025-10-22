"""
Модуль конфигурации приложения.

Загружает переменные окружения и предоставляет настройки для всего приложения.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


## Класс настроек приложения
class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    
    Загружает все необходимые переменные окружения и валидирует их.
    Использует pydantic-settings для автоматической загрузки из .env файла.
    
    :ivar bot_token: Токен Telegram бота
    :ivar agentrouter_api_key: API ключ для AgentRouter
    :ivar database_url: URL для подключения к PostgreSQL
    :ivar redis_url: URL для подключения к Redis
    :ivar log_level: Уровень логирования
    :ivar log_file: Путь к файлу логов
    :ivar max_transaction_amount: Максимальная сумма транзакции
    :ivar rate_limit_requests: Количество запросов в период
    :ivar rate_limit_period: Период для rate limit в секундах
    """
    
    bot_token: str = Field(..., description="Токен Telegram бота")
    agentrouter_api_key: str = Field(default="", description="API ключ AgentRouter (опционально)")
    database_url: str = Field(..., description="URL базы данных PostgreSQL")
    redis_url: str = Field(default="redis://localhost:6379/0", description="URL Redis")
    
    log_level: str = Field(default="INFO", description="Уровень логирования")
    log_file: str = Field(default="logs/bot.log", description="Путь к файлу логов")
    
    max_transaction_amount: int = Field(default=1000000, description="Максимальная сумма транзакции")
    rate_limit_requests: int = Field(default=30, description="Количество запросов в период")
    rate_limit_period: int = Field(default=60, description="Период rate limit в секундах")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Валидация уровня логирования.
        
        :param v: Значение уровня логирования
        :return: Валидированный уровень в верхнем регистре
        :raises ValueError: Если уровень логирования некорректен
        """
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v_upper
    
    @field_validator("max_transaction_amount")
    @classmethod
    def validate_max_amount(cls, v: int) -> int:
        """
        Валидация максимальной суммы транзакции.
        
        :param v: Значение максимальной суммы
        :return: Валидированная сумма
        :raises ValueError: Если сумма меньше или равна нулю
        """
        if v <= 0:
            raise ValueError("Max transaction amount must be positive")
        return v


## Глобальный экземпляр настроек
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Получить экземпляр настроек приложения.
    
    Создает новый экземпляр при первом вызове, затем возвращает существующий.
    Используется паттерн Singleton для единого экземпляра настроек.
    
    :return: Экземпляр класса Settings с загруженными настройками
    
    Example:
        >>> settings = get_settings()
        >>> print(settings.bot_token)
    """
    global settings
    if settings is None:
        settings = Settings()
    return settings


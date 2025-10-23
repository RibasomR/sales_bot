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
    
    bot_token: str = Field(..., validation_alias="BOT_TOKEN", description="Токен Telegram бота")
    agentrouter_api_key: str = Field(default="", validation_alias="AGENTROUTER_API_KEY", description="API ключ AgentRouter (опционально)")
    database_url: str = Field(..., validation_alias="DATABASE_URL", description="URL базы данных PostgreSQL")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL", description="URL Redis")
    
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL", description="Уровень логирования")
    log_file: str = Field(default="logs/bot.log", validation_alias="LOG_FILE", description="Путь к файлу логов")
    
    max_transaction_amount: int = Field(default=1000000, validation_alias="MAX_TRANSACTION_AMOUNT", description="Максимальная сумма транзакции")
    rate_limit_requests: int = Field(default=30, validation_alias="RATE_LIMIT_REQUESTS", description="Количество запросов в период")
    rate_limit_period: int = Field(default=60, validation_alias="RATE_LIMIT_PERIOD", description="Период rate limit в секундах")
    
    ## AgentRouter API retry and timeout settings
    agentrouter_max_retries: int = Field(default=3, validation_alias="AGENTROUTER_MAX_RETRIES", description="Maximum number of retry attempts for AgentRouter API")
    agentrouter_timeout: int = Field(default=10, validation_alias="AGENTROUTER_TIMEOUT", description="Timeout for single AgentRouter API request in seconds")
    agentrouter_total_deadline: int = Field(default=25, validation_alias="AGENTROUTER_TOTAL_DEADLINE", description="Total deadline for all AgentRouter API attempts in seconds")
    agentrouter_max_text_length: int = Field(default=1000, validation_alias="AGENTROUTER_MAX_TEXT_LENGTH", description="Maximum length of text to send to AgentRouter API")
    
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


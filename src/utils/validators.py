"""
Утилиты для валидации входных данных.

Содержит функции для проверки и очистки пользовательских данных
для защиты от инъекций и других уязвимостей.
"""

import re
import html
from typing import Optional
from decimal import Decimal, InvalidOperation

## Защита от XSS: очистка HTML-тегов
def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Очистить текст от потенциально опасных символов и HTML.
    
    Экранирует HTML-теги для защиты от XSS атак.
    
    :param text: Текст для очистки
    :param max_length: Максимальная длина текста (опционально)
    :return: Очищенный текст
    
    Example:
        >>> sanitize_text("<script>alert('XSS')</script>")
        "&lt;script&gt;alert('XSS')&lt;/script&gt;"
    """
    if not text:
        return ""
    
    text = text.strip()
    
    # Экранируем HTML
    text = html.escape(text)
    
    # Удаляем управляющие символы (кроме переноса строки и табуляции)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


## Валидация суммы транзакции
def validate_amount(amount_str: str) -> tuple[bool, Optional[float], Optional[str]]:
    """
    Валидировать строку суммы транзакции.
    
    Проверяет, что сумма является положительным числом в допустимых пределах.
    
    :param amount_str: Строка с суммой
    :return: Кортеж (валидна, сумма, сообщение об ошибке)
    
    Example:
        >>> validate_amount("500")
        (True, 500.0, None)
        >>> validate_amount("-100")
        (False, None, "Сумма должна быть положительной")
    """
    try:
        # Очищаем от валюты и пробелов
        cleaned = amount_str.replace(",", ".").replace("₽", "").replace(" ", "")
        
        # Проверяем формат числа
        if not re.match(r'^\d+(\.\d{1,2})?$', cleaned):
            return False, None, "❌ Некорректный формат суммы. Используйте только цифры и точку."
        
        amount = float(cleaned)
        
        if amount <= 0:
            return False, None, "❌ Сумма должна быть положительной."
        
        if amount > 10_000_000:
            return False, None, "❌ Сумма слишком большая (максимум 10 000 000)."
        
        # Проверяем количество знаков после запятой
        decimal_amount = Decimal(cleaned)
        if decimal_amount.as_tuple().exponent < -2:
            return False, None, "❌ Слишком много знаков после запятой (максимум 2)."
        
        return True, amount, None
        
    except (ValueError, InvalidOperation):
        return False, None, "❌ Некорректный формат суммы. Введите число."


## Валидация названия категории
def validate_category_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Валидировать название категории.
    
    Проверяет длину и допустимые символы в названии категории.
    
    :param name: Название категории
    :return: Кортеж (валидно, сообщение об ошибке)
    
    Example:
        >>> validate_category_name("Продукты")
        (True, None)
        >>> validate_category_name("A")
        (False, "❌ Название слишком короткое (минимум 2 символа).")
    """
    name = name.strip()
    
    if len(name) < 2:
        return False, "❌ Название слишком короткое (минимум 2 символа)."
    
    if len(name) > 50:
        return False, "❌ Название слишком длинное (максимум 50 символов)."
    
    # Проверяем на опасные символы
    if re.search(r'[<>\"\'`]', name):
        return False, "❌ Название содержит недопустимые символы."
    
    return True, None


## Валидация описания транзакции
def validate_description(description: str) -> tuple[bool, Optional[str]]:
    """
    Валидировать описание транзакции.
    
    :param description: Описание транзакции
    :return: Кортеж (валидно, сообщение об ошибке)
    
    Example:
        >>> validate_description("Покупка в магазине")
        (True, None)
    """
    if len(description) > 500:
        return False, "❌ Описание слишком длинное (максимум 500 символов)."
    
    return True, None


## Валидация эмодзи
def validate_emoji(emoji: str) -> tuple[bool, Optional[str]]:
    """
    Валидировать эмодзи для категории.
    
    Проверяет, что строка содержит только эмодзи.
    
    :param emoji: Строка с эмодзи
    :return: Кортеж (валидно, сообщение об ошибке)
    
    Example:
        >>> validate_emoji("🛒")
        (True, None)
        >>> validate_emoji("ABC")
        (False, "❌ Должен быть эмодзи.")
    """
    # Простая проверка на эмодзи (Unicode ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    if not emoji_pattern.match(emoji):
        return False, "❌ Должен быть эмодзи."
    
    if len(emoji) > 10:
        return False, "❌ Слишком много эмодзи (максимум 10 символов)."
    
    return True, None


## Проверка лимита запросов (simple rate limiting)
class RateLimiter:
    """
    Простой rate limiter для ограничения частоты запросов.
    
    Использует словарь в памяти для отслеживания количества запросов.
    Для продакшена лучше использовать Redis.
    """
    
    def __init__(self):
        """Инициализация rate limiter."""
        self._requests: dict[int, list[float]] = {}
    
    def check_rate_limit(
        self,
        user_id: int,
        max_requests: int = 10,
        time_window: int = 60
    ) -> tuple[bool, Optional[str]]:
        """
        Проверить лимит запросов для пользователя.
        
        :param user_id: ID пользователя
        :param max_requests: Максимальное количество запросов
        :param time_window: Временное окно в секундах
        :return: Кортеж (разрешено, сообщение об ошибке)
        
        Example:
            >>> limiter = RateLimiter()
            >>> allowed, error = limiter.check_rate_limit(user_id=123)
        """
        import time
        
        current_time = time.time()
        
        if user_id not in self._requests:
            self._requests[user_id] = []
        
        # Удаляем старые запросы
        self._requests[user_id] = [
            req_time for req_time in self._requests[user_id]
            if current_time - req_time < time_window
        ]
        
        # Проверяем лимит
        if len(self._requests[user_id]) >= max_requests:
            return False, f"⏱ Слишком много запросов. Попробуйте через {time_window} секунд."
        
        # Добавляем текущий запрос
        self._requests[user_id].append(current_time)
        
        return True, None


## Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()


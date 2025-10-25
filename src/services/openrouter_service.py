"""
Service for working with local Whisper and parsing transactions via AgentRouter API.

Provides transcription of voice messages via local Whisper
and parsing of transaction text via AgentRouter API (DeepSeek V3.2).
"""

import asyncio
import json
import random
import time
from typing import Optional, Dict, Any
from pathlib import Path
from decimal import Decimal, InvalidOperation

import httpx
from pywhispercpp.model import Model
from pywhispercpp.utils import download_model
from loguru import logger

from config import get_settings


## Model configuration
WHISPER_MODEL_NAME = "base"
AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"
AGENTROUTER_MODEL = "deepseek-v3.2"

## Global variable for storing loaded Whisper.cpp model
_whisper_model = None


class AgentRouterError(Exception):
    """
    Base exception for AgentRouter API errors.
    """
    pass


class TranscriptionError(AgentRouterError):
    """
    Error during audio transcription.
    """
    pass


class ParsingError(AgentRouterError):
    """
    Error during transaction text parsing.
    """
    pass


## Load Whisper.cpp model asynchronously
async def _load_whisper_model():
    """
    Load Whisper.cpp model into memory (lazy loading).
    
    Model is loaded once on first call and kept in memory.
    Uses 'base' model as a compromise between speed and accuracy.
    Whisper.cpp provides 2-4x better performance than openai-whisper.
    
    :return: Loaded Whisper.cpp model
    :raises TranscriptionError: If model loading fails
    """
    global _whisper_model
    
    if _whisper_model is None:
        logger.info(f"Загружаю модель Whisper.cpp: {WHISPER_MODEL_NAME}")
        try:
            ## Ensure model is downloaded first (cached if already exists)
            logger.info(f"Проверяю наличие модели {WHISPER_MODEL_NAME}...")
            model_path = await asyncio.to_thread(download_model, WHISPER_MODEL_NAME)
            logger.success(f"Модель найдена: {model_path}")
            
            ## Load model in thread to avoid blocking event loop
            ## Pass model name directly - pywhispercpp handles the rest
            _whisper_model = await asyncio.to_thread(
                Model,
                WHISPER_MODEL_NAME,
                n_threads=4
            )
            logger.success(f"Модель Whisper.cpp '{WHISPER_MODEL_NAME}' успешно загружена")
        except Exception as e:
            from src.utils.sanitizer import sanitize_exception_message
            safe_error = sanitize_exception_message(e)
            logger.error(f"Ошибка загрузки модели Whisper.cpp: {safe_error}")
            raise TranscriptionError(f"Не удалось загрузить модель Whisper.cpp: {safe_error}")
    
    return _whisper_model


## Initialize Whisper model on startup
async def initialize_whisper():
    """
    Initialize Whisper model during bot startup.
    
    Preloads model to avoid delays on first voice message.
    Should be called during bot initialization.
    
    :return: None
    :raises TranscriptionError: If model loading fails
    """
    await _load_whisper_model()
    logger.info("Whisper.cpp готов к работе")


## Transcribe audio to text via local Whisper.cpp
async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file to text via local Whisper.cpp.
    
    Uses locally installed Whisper.cpp model to convert speech to text.
    Provides 2-4x better performance compared to openai-whisper.
    Works completely offline, requires no API keys and is free.
    
    :param audio_path: Path to audio file
    :return: Recognized text
    :raises TranscriptionError: If transcription fails
    :raises FileNotFoundError: If audio file not found
    
    Example:
        >>> text = await transcribe_audio("voice_message.ogg")
        >>> print(text)
        "Потратил 500 рублей на продукты"
    """
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")
    
    logger.info(f"Начинаю транскрипцию аудио через Whisper.cpp: {audio_path}")
    
    try:
        model = await _load_whisper_model()
        
        ## Transcribe with Whisper.cpp
        result = await asyncio.to_thread(
            model.transcribe,
            audio_path,
            language="ru"
        )
        
        ## model.transcribe() returns list of segment objects with .text attribute
        if isinstance(result, str):
            text = result.strip()
        elif isinstance(result, list) and result:
            ## Each segment is an object with .text, .t0, .t1 attributes
            text = " ".join(segment.text for segment in result if hasattr(segment, 'text')).strip()
        else:
            raise TranscriptionError(f"Неожиданный тип результата транскрипции: {type(result)}")
        
        if not text:
            raise TranscriptionError("Пустой результат транскрипции")
        
        logger.success(f"Успешно транскрибировано через Whisper.cpp: '{text[:100]}...'")
        return text
        
    except FileNotFoundError:
        raise
    except TranscriptionError:
        raise
    except Exception as e:
        from src.utils.sanitizer import sanitize_exception_message
        safe_error = sanitize_exception_message(e)
        logger.error(f"Ошибка при транскрипции через Whisper.cpp: {safe_error}")
        raise TranscriptionError(f"Не удалось транскрибировать аудио: {safe_error}")


## Calculate exponential backoff delay with jitter
def _calculate_backoff_delay(attempt: int, base_delay: float = 0.5, jitter_percent: float = 0.2) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Uses formula: base_delay * (2 ^ attempt) ± jitter_percent
    Example delays: 0.5s, 1s, 2s with ±20% jitter
    
    :param attempt: Current attempt number (0-based)
    :param base_delay: Base delay in seconds
    :param jitter_percent: Jitter percentage (0.0-1.0)
    :return: Delay in seconds with jitter applied
    
    Example:
        >>> delay = _calculate_backoff_delay(0)  # ~0.4-0.6s
        >>> delay = _calculate_backoff_delay(1)  # ~0.8-1.2s
        >>> delay = _calculate_backoff_delay(2)  # ~1.6-2.4s
    """
    exponential_delay = base_delay * (2 ** attempt)
    jitter = exponential_delay * jitter_percent * (2 * random.random() - 1)
    return exponential_delay + jitter


## Parse transaction text via AgentRouter API
async def parse_transaction_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse transaction text via AgentRouter API (DeepSeek V3.2).
    
    Sends text to LLM to extract structured data:
    - Operation type (income/expense)
    - Amount (in rubles)
    - Category
    - Description
    
    Uses exponential backoff with jitter for retries and enforces total deadline.
    
    :param text: Text to parse (will be truncated to max_text_length)
    :return: Dictionary with recognized data or None on error
    :raises ParsingError: On critical parsing error
    
    Example:
        >>> data = await parse_transaction_text("Потратил 500 рублей на продукты")
        >>> print(data)
        {
            "type": "expense",
            "amount": Decimal('500'),
            "category": "Продукты",
            "description": None
        }
    """
    if not text or not text.strip():
        raise ParsingError("Текст для парсинга пустой")
    
    settings = get_settings()
    
    ## Truncate text to maximum allowed length
    if len(text) > settings.agentrouter_max_text_length:
        logger.warning(f"Text truncated from {len(text)} to {settings.agentrouter_max_text_length} characters")
        text = text[:settings.agentrouter_max_text_length]
    
    logger.info(f"Парсинг текста транзакции через AgentRouter: '{text[:50]}...'")
    
    if not settings.agentrouter_api_key:
        raise ParsingError(
            "AgentRouter API ключ не настроен. "
            "Добавьте AGENTROUTER_API_KEY в .env файл. "
            "Получить ключ: https://agentrouter.org/console/token"
        )
    
    from src.utils.sanitizer import sanitize_headers, mask_sensitive_value
    
    # Mask API key for logging
    safe_api_key = mask_sensitive_value(settings.agentrouter_api_key, visible_chars=4)
    
    ## Prompt for parsing transaction via LLM
    prompt = """Проанализируй текст и извлеки информацию о финансовой транзакции.
Верни JSON с полями:
- type: "income" или "expense"
- amount: число (только сумма в рублях, без валюты)
- category: строка (категория транзакции)
- description: строка или null (дополнительное описание)

Категории расходов: Продукты, Транспорт, Рестораны, Здоровье, Дом, Развлечения, Одежда, Другое
Категории доходов: Зарплата, Фриланс, Подарок, Инвестиции, Другое

Если чего-то нет - используй null.
Если "тысяч" или "тыс" - умножь сумму на 1000.

Текст: "{text}"

Верни ТОЛЬКО JSON, без дополнительного текста.""".format(text=text)
    
    ## Send request to AgentRouter
    headers = {
        "Authorization": f"Bearer {settings.agentrouter_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": AGENTROUTER_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 500
    }
    
    ## Track total time spent for deadline enforcement
    start_time = time.monotonic()
    last_error = None
    
    for attempt in range(settings.agentrouter_max_retries):
        ## Check if we exceeded total deadline
        elapsed = time.monotonic() - start_time
        if elapsed >= settings.agentrouter_total_deadline:
            logger.error(f"Total deadline exceeded: {elapsed:.2f}s >= {settings.agentrouter_total_deadline}s")
            raise ParsingError(
                f"AgentRouter API не ответил за отведенное время ({settings.agentrouter_total_deadline}s). "
                "Попробуйте позже."
            )
        
        ## Calculate remaining time for this attempt
        remaining_time = settings.agentrouter_total_deadline - elapsed
        attempt_timeout = min(settings.agentrouter_timeout, remaining_time)
        
        try:
            async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                response = await client.post(
                    f"{AGENTROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    # Sanitize response for logging (may contain sensitive data)
                    safe_response = response.text[:200] if len(response.text) > 200 else response.text
                    logger.error(f"AgentRouter API ошибка {response.status_code}: {safe_response}")
                    
                    ## Handle authentication errors (401)
                    if response.status_code == 401:
                        raise ParsingError(
                            "Неверный API ключ AgentRouter. "
                            "Проверьте AGENTROUTER_API_KEY в .env файле. "
                            "Получить новый ключ: https://agentrouter.org/console/token"
                        )
                    
                    last_error = ParsingError(f"AgentRouter API вернул ошибку: {response.status_code}")
                    
                    if attempt < settings.agentrouter_max_retries - 1:
                        delay = _calculate_backoff_delay(attempt)
                        logger.info(f"Повтор через {delay:.2f}s (попытка {attempt + 1}/{settings.agentrouter_max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    raise last_error
                
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                ## Extract JSON from response (may be wrapped in ```json```)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                transaction_data = json.loads(content)
                
                ## Validate data
                if not transaction_data.get("type") in ["income", "expense"]:
                    raise ParsingError("Некорректный тип транзакции")
                
                ## Convert amount to Decimal for precision
                try:
                    amount = Decimal(str(transaction_data.get("amount", 0)))
                except (ValueError, InvalidOperation):
                    raise ParsingError("Некорректный формат суммы")
                
                if amount <= 0:
                    raise ParsingError("Некорректная сумма транзакции")
                
                if amount > 10_000_000:
                    raise ParsingError("Сумма слишком большая (максимум 10 000 000)")
                
                ## Replace amount with Decimal
                transaction_data["amount"] = amount
                
                logger.success(f"Успешно распознано через AgentRouter: {transaction_data}")
                return transaction_data
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout при запросе к AgentRouter (попытка {attempt + 1}/{settings.agentrouter_max_retries})")
            last_error = ParsingError(
                "AgentRouter API недоступен (timeout). "
                "Проверьте интернет соединение и попробуйте позже."
            )
            
            if attempt < settings.agentrouter_max_retries - 1:
                delay = _calculate_backoff_delay(attempt)
                logger.info(f"Повтор через {delay:.2f}s")
                await asyncio.sleep(delay)
                continue
            raise last_error
            
        except (json.JSONDecodeError, KeyError) as e:
            from src.utils.sanitizer import sanitize_exception_message
            safe_error = sanitize_exception_message(e)
            logger.error(f"Ошибка парсинга ответа от AgentRouter: {safe_error}")
            last_error = ParsingError(
                "Не удалось обработать ответ от AgentRouter API. "
                "Попробуйте еще раз или обратитесь к администратору."
            )
            
            if attempt < settings.agentrouter_max_retries - 1:
                delay = _calculate_backoff_delay(attempt)
                logger.info(f"Повтор через {delay:.2f}s")
                await asyncio.sleep(delay)
                continue
            raise last_error
            
        except ParsingError:
            ## Re-raise parsing errors without retry
            raise
            
        except Exception as e:
            from src.utils.sanitizer import sanitize_exception_message
            safe_error = sanitize_exception_message(e)
            logger.error(f"Неожиданная ошибка при запросе к AgentRouter: {safe_error}")
            last_error = ParsingError(f"Ошибка при обращении к AgentRouter API: {safe_error}")
            
            if attempt < settings.agentrouter_max_retries - 1:
                delay = _calculate_backoff_delay(attempt)
                logger.info(f"Повтор через {delay:.2f}s")
                await asyncio.sleep(delay)
                continue
            raise last_error
    
    ## If we exhausted all retries, raise the last error
    if last_error:
        raise last_error
    
    raise ParsingError(
        "Все попытки обращения к AgentRouter API провалились. "
        "Попробуйте позже."
    )


## Find category by name with similarity matching
def find_matching_category(
    category_name: Optional[str],
    available_categories: list,
    default_category_name: str = "Другое"
) -> tuple[Optional[int], str]:
    """
    Find matching category by name from recognized text.
    
    Searches for category by partial name match (case-insensitive).
    If not found - returns "Другое" category.
    
    :param category_name: Category name from recognized text
    :param available_categories: List of available categories (Category objects)
    :param default_category_name: Default category name
    :return: Tuple (category_id, category_display_name)
    
    Example:
        >>> categories = [Category(id=1, name="Продукты"), Category(id=2, name="Другое")]
        >>> category_id, name = find_matching_category("прод", categories)
        >>> print(category_id, name)
        1 "Продукты"
    """
    if not category_name:
        # Ищем категорию "Другое"
        for cat in available_categories:
            if cat.name == default_category_name:
                return cat.id, cat.name
        return None, default_category_name
    
    category_name_lower = category_name.lower().strip()
    
    # Поиск точного совпадения
    for cat in available_categories:
        if cat.name.lower() == category_name_lower:
            return cat.id, cat.name
    
    # Поиск частичного совпадения
    for cat in available_categories:
        if category_name_lower in cat.name.lower() or cat.name.lower() in category_name_lower:
            return cat.id, cat.name
    
    # Не найдено - возвращаем "Другое"
    for cat in available_categories:
        if cat.name == default_category_name:
            return cat.id, cat.name
    
    return None, default_category_name


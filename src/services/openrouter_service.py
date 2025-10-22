"""
Service for working with local Whisper and parsing transactions via AgentRouter API.

Provides transcription of voice messages via local Whisper
and parsing of transaction text via AgentRouter API (DeepSeek V3.2).
"""

import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
import whisper
from loguru import logger

from config import get_settings


## Model configuration
WHISPER_MODEL_NAME = "base"
AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"
DEEPSEEK_MODEL = "deepseek-v3.2"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

## Глобальная переменная для хранения загруженной модели Whisper
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


## Load Whisper model (synchronous)
def _load_whisper_model():
    """
    Load Whisper model into memory (lazy loading).
    
    Model is loaded once on first call and kept in memory.
    Uses 'base' model as a compromise between speed and accuracy.
    
    :return: Loaded Whisper model
    :raises TranscriptionError: If model loading fails
    """
    global _whisper_model
    
    if _whisper_model is None:
        logger.info(f"Загружаю модель Whisper: {WHISPER_MODEL_NAME}")
        try:
            _whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
            logger.success(f"Модель Whisper '{WHISPER_MODEL_NAME}' успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели Whisper: {e}")
            raise TranscriptionError(f"Не удалось загрузить модель Whisper: {e}")
    
    return _whisper_model


## Transcribe audio to text via local Whisper
async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file to text via local Whisper.
    
    Uses locally installed Whisper model to convert speech to text.
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
    
    logger.info(f"Начинаю транскрипцию аудио: {audio_path}")
    
    try:
        model = _load_whisper_model()
        
        result = await asyncio.to_thread(
            model.transcribe,
            audio_path,
            language="ru",
            fp16=False
        )
        
        text = result["text"].strip()
        
        if not text:
            raise TranscriptionError("Пустой результат транскрипции")
        
        logger.success(f"Успешно транскрибировано: '{text[:100]}...'")
        return text
        
    except FileNotFoundError:
        raise
    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при транскрипции: {e}")
        raise TranscriptionError(f"Не удалось транскрибировать аудио: {e}")


## Parse transaction text via AgentRouter API
async def parse_transaction_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse transaction text via AgentRouter API (DeepSeek V3.2).
    
    Sends text to LLM to extract structured data:
    - Operation type (income/expense)
    - Amount (in rubles)
    - Category
    - Description
    
    :param text: Text to parse
    :return: Dictionary with recognized data or None on error
    :raises ParsingError: On critical parsing error
    
    Example:
        >>> data = await parse_transaction_text("Потратил 500 рублей на продукты")
        >>> print(data)
        {
            "type": "expense",
            "amount": 500.0,
            "category": "Продукты",
            "description": None
        }
    """
    if not text or not text.strip():
        raise ParsingError("Текст для парсинга пустой")
    
    logger.info(f"Парсинг текста транзакции через AgentRouter: '{text[:50]}...'")
    
    settings = get_settings()
    
    if not settings.agentrouter_api_key:
        raise ParsingError(
            "AgentRouter API ключ не настроен. "
            "Добавьте AGENTROUTER_API_KEY в .env файл. "
            "Получить ключ: https://agentrouter.org/console/token"
        )
    
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
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 500
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{AGENTROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"AgentRouter API ошибка {response.status_code}: {response.text}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(1)
                        continue
                    raise ParsingError(f"AgentRouter API вернул ошибку: {response.status_code}")
                
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
                
                if not transaction_data.get("amount") or transaction_data["amount"] <= 0:
                    raise ParsingError("Некорректная сумма транзакции")
                
                if transaction_data["amount"] > 10_000_000:
                    raise ParsingError("Сумма слишком большая (максимум 10 000 000)")
                
                logger.success(f"Успешно распознано через AgentRouter: {transaction_data}")
                return transaction_data
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout при запросе к AgentRouter (попытка {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
                continue
            raise ParsingError(
                "AgentRouter API недоступен (timeout). "
                "Проверьте интернет соединение и попробуйте позже."
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Ошибка парсинга ответа от AgentRouter: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            raise ParsingError(
                "Не удалось обработать ответ от AgentRouter API. "
                "Попробуйте еще раз или обратитесь к администратору."
            )
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к AgentRouter: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
                continue
            raise ParsingError(
                f"Ошибка при обращении к AgentRouter API: {str(e)}"
            )
    
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


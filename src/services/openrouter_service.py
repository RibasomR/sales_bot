"""
Сервис для работы с локальным Whisper и парсинга транзакций через OpenRouter API.

Обеспечивает транскрипцию голосовых сообщений через локальный Whisper
и парсинг текста транзакций через OpenRouter API (DeepSeek V3.1).
"""

import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
import whisper
from loguru import logger

from config import get_settings


## Конфигурация моделей
WHISPER_MODEL_NAME = "base"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEEPSEEK_MODEL = "deepseek/deepseek-chat"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

## Глобальная переменная для хранения загруженной модели Whisper
_whisper_model = None


class OpenRouterError(Exception):
    """
    Базовое исключение для ошибок OpenRouter API.
    """
    pass


class TranscriptionError(OpenRouterError):
    """
    Ошибка при транскрипции аудио.
    """
    pass


class ParsingError(OpenRouterError):
    """
    Ошибка при парсинге текста транзакции.
    """
    pass


## Загрузка модели Whisper (синхронная)
def _load_whisper_model():
    """
    Загрузить модель Whisper в память (ленивая загрузка).
    
    Модель загружается один раз при первом вызове и сохраняется в памяти.
    Используется модель 'base' как компромисс между скоростью и точностью.
    
    :return: Загруженная модель Whisper
    :raises TranscriptionError: При ошибке загрузки модели
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


## Транскрипция аудио в текст через локальный Whisper
async def transcribe_audio(audio_path: str) -> str:
    """
    Транскрибировать аудиофайл в текст через локальный Whisper.
    
    Использует локально установленную модель Whisper для преобразования речи в текст.
    Работает полностью офлайн, не требует API ключей и бесплатна.
    
    :param audio_path: Путь к аудиофайлу
    :return: Распознанный текст
    :raises TranscriptionError: При ошибке транскрипции
    :raises FileNotFoundError: Если аудиофайл не найден
    
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


## Парсинг текста транзакции через OpenRouter API
async def parse_transaction_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Парсинг текста транзакции через OpenRouter API (DeepSeek V3.1).
    
    Отправляет текст в LLM для извлечения структурированных данных:
    - Тип операции (income/expense)
    - Сумму (в рублях)
    - Категорию
    - Описание
    
    :param text: Текст для парсинга
    :return: Словарь с распознанными данными или None при ошибке
    :raises ParsingError: При критической ошибке парсинга
    
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
    
    logger.info(f"Парсинг текста транзакции через OpenRouter: '{text[:50]}...'")
    
    settings = get_settings()
    
    if not settings.openrouter_api_key:
        raise ParsingError(
            "OpenRouter API ключ не настроен. "
            "Добавьте OPENROUTER_API_KEY в .env файл. "
            "Инструкция: docs/openrouter_setup.md"
        )
    
    ## Промпт для парсинга транзакции через LLM
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
    
    ## Отправляем запрос в OpenRouter
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://github.com/your-repo",
        "X-Title": "Finance Bot"
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
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"OpenRouter API ошибка {response.status_code}: {response.text}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(1)
                        continue
                    raise ParsingError(f"OpenRouter API вернул ошибку: {response.status_code}")
                
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                ## Извлекаем JSON из ответа (может быть обёрнут в ```json```)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                transaction_data = json.loads(content)
                
                ## Валидация данных
                if not transaction_data.get("type") in ["income", "expense"]:
                    raise ParsingError("Некорректный тип транзакции")
                
                if not transaction_data.get("amount") or transaction_data["amount"] <= 0:
                    raise ParsingError("Некорректная сумма транзакции")
                
                if transaction_data["amount"] > 10_000_000:
                    raise ParsingError("Сумма слишком большая (максимум 10 000 000)")
                
                logger.success(f"Успешно распознано через OpenRouter: {transaction_data}")
                return transaction_data
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout при запросе к OpenRouter (попытка {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
                continue
            raise ParsingError(
                "OpenRouter API недоступен (timeout). "
                "Проверьте интернет соединение и попробуйте позже."
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Ошибка парсинга ответа от OpenRouter: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            raise ParsingError(
                "Не удалось обработать ответ от OpenRouter API. "
                "Попробуйте еще раз или обратитесь к администратору."
            )
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к OpenRouter: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2)
                continue
            raise ParsingError(
                f"Ошибка при обращении к OpenRouter API: {str(e)}"
            )
    
    raise ParsingError(
        "Все попытки обращения к OpenRouter API провалились. "
        "Попробуйте позже."
    )


## Найти категорию по названию с учетом похожести
def find_matching_category(
    category_name: Optional[str],
    available_categories: list,
    default_category_name: str = "Другое"
) -> tuple[Optional[int], str]:
    """
    Найти подходящую категорию по названию из распознанного текста.
    
    Ищет категорию по частичному совпадению названия (без учета регистра).
    Если не найдена - возвращает категорию "Другое".
    
    :param category_name: Название категории из распознанного текста
    :param available_categories: Список доступных категорий (Category объекты)
    :param default_category_name: Название категории по умолчанию
    :return: Кортеж (category_id, category_display_name)
    
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


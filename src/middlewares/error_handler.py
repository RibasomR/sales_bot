"""
Middleware для централизованной обработки ошибок.

Перехватывает все исключения в handlers и обрабатывает их единообразно.
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramNotFound,
    TelegramUnauthorizedError,
    TelegramForbiddenError
)
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from config import get_settings


## Middleware для обработки ошибок
class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware для централизованной обработки ошибок.
    
    Перехватывает исключения различных типов и предоставляет
    пользователю понятные сообщения об ошибках.
    
    Обрабатывает:
    - Ошибки Telegram API
    - Ошибки базы данных (SQLAlchemy)
    - Ошибки валидации данных
    - Прочие необработанные исключения
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с перехватом исключений.
        
        :param handler: Следующий обработчик в цепочке
        :param event: Объект обновления от Telegram
        :param data: Дополнительные данные
        :return: Результат выполнения обработчика или None при ошибке
        """
        try:
            return await handler(event, data)
            
        except TelegramUnauthorizedError as e:
            logger.critical(f"🚨 Telegram Unauthorized: {e}")
            await self._send_error_message(
                event,
                "❌ Ошибка авторизации бота. Свяжись с администратором."
            )
            
        except TelegramForbiddenError as e:
            logger.warning(f"⚠️ Telegram Forbidden: {e}")
            
        except TelegramBadRequest as e:
            logger.error(f"❌ Telegram BadRequest: {e}")
            await self._send_error_message(
                event,
                "❌ Некорректный запрос. Попробуй еще раз."
            )
            
        except TelegramNotFound as e:
            logger.warning(f"⚠️ Telegram NotFound: {e}")
            
        except TelegramAPIError as e:
            logger.error(f"❌ Telegram API Error: {e}")
            await self._send_error_message(
                event,
                "❌ Ошибка связи с Telegram. Попробуй позже."
            )
            
        except SQLAlchemyError as e:
            logger.error(f"🗄️ Database Error: {e}")
            await self._send_error_message(
                event,
                "❌ Ошибка базы данных. Попробуй позже или обратись к администратору."
            )
            
        except ValueError as e:
            logger.warning(f"⚠️ ValueError: {e}")
            await self._send_error_message(
                event,
                f"❌ Некорректные данные: {str(e)}"
            )
            
        except Exception as e:
            logger.exception(f"💥 Необработанное исключение: {e}")
            await self._send_error_message(
                event,
                "❌ Произошла непредвиденная ошибка. Попробуй позже."
            )
    
    async def _send_error_message(self, event: Update, text: str) -> None:
        """
        Отправить сообщение об ошибке пользователю.
        
        :param event: Объект обновления от Telegram
        :param text: Текст сообщения об ошибке
        :return: None
        """
        try:
            # Получаем объект для отправки сообщения
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                if event.message:
                    await event.message.answer(text)
                else:
                    await event.answer(text, show_alert=True)
            elif hasattr(event, 'message') and event.message:
                await event.message.answer(text)
            elif hasattr(event, 'callback_query') and event.callback_query:
                if event.callback_query.message:
                    await event.callback_query.message.answer(text)
                else:
                    await event.callback_query.answer(text, show_alert=True)
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e}")


## Функция-fallback для недоступности БД
async def database_fallback_message(event: Update) -> None:
    """
    Отправить сообщение при недоступности базы данных.
    
    :param event: Объект обновления от Telegram
    :return: None
    """
    text = (
        "🔧 База данных временно недоступна.\n"
        "Пожалуйста, попробуй позже или обратись к администратору."
    )
    
    try:
        if event.message:
            await event.message.answer(text)
        elif event.callback_query:
            await event.callback_query.answer(text, show_alert=True)
    except Exception as e:
        logger.error(f"❌ Не удалось отправить fallback сообщение: {e}")


## Fallback function for AgentRouter API unavailability
async def api_fallback_message(event: Update) -> None:
    """
    Send message when AgentRouter API is unavailable.
    
    :param event: Update object from Telegram
    :return: None
    """
    text = (
        "🔧 Сервис распознавания голоса временно недоступен.\n"
        "Используй ручной ввод транзакций: /add"
    )
    
    try:
        if event.message:
            await event.message.answer(text)
        elif event.callback_query:
            await event.callback_query.answer(text, show_alert=True)
    except Exception as e:
        logger.error(f"❌ Не удалось отправить fallback сообщение: {e}")


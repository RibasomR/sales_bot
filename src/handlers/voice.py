"""
Обработчики для работы с голосовыми сообщениями.

Содержит хендлеры для:
- Обработки голосовых сообщений
- Подтверждения распознанной транзакции
- Редактирования полей транзакции
- Отмены операции
"""

import os
from pathlib import Path
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Voice
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import get_settings
from src.states import VoiceTransactionStates
from src.keyboards.voice_keyboards import (
    get_voice_confirmation_keyboard,
    get_voice_edit_keyboard,
    get_voice_categories_keyboard,
    get_voice_edit_cancel_keyboard,
)
from src.services.database import (
    get_or_create_user,
    get_categories,
    create_transaction,
)
from src.services.openrouter_service import (
    transcribe_audio,
    parse_transaction_text,
    find_matching_category,
    TranscriptionError,
    ParsingError,
)
from src.models import CategoryType, TransactionType


router = Router(name="voice")


## Обработка голосового сообщения
@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext) -> None:
    """
    Voice message handler.
    
    Downloads audio file, converts to text via AgentRouter,
    parses transaction and shows confirmation to user.
    
    :param message: Message with voice file
    :param state: FSM context
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    
    processing_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    voice: Voice = message.voice
    audio_path = None
    
    try:
        file = await message.bot.get_file(voice.file_id)
        
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        audio_path = temp_dir / f"{message.from_user.id}_{voice.file_unique_id}.ogg"
        
        await message.bot.download_file(file.file_path, audio_path)
        logger.info(f"Голосовое сообщение сохранено: {audio_path}")
        
        await processing_msg.edit_text("🎧 Распознаю речь...")
        text = await transcribe_audio(str(audio_path))
        logger.info(f"Текст распознан: {text}")
        
        await processing_msg.edit_text("🤔 Анализирую текст...")
        transaction_data = await parse_transaction_text(text)
        
        if not transaction_data:
            await processing_msg.edit_text(
                "❌ Не удалось распознать транзакцию.\n\n"
                "Попробуйте сформулировать по-другому или используйте /add"
            )
            return
        
        transaction_type = transaction_data["type"]
        category_type = CategoryType.EXPENSE if transaction_type == "expense" else CategoryType.INCOME
        
        categories = await get_categories(
            user_id=user.id,
            category_type=category_type,
            include_default=True
        )
        
        category_id, category_name = find_matching_category(
            transaction_data.get("category"),
            categories
        )
        
        if not category_id:
            await processing_msg.edit_text(
                "❌ Не удалось определить категорию.\n\n"
                "Попробуйте использовать команду /add"
            )
            return
        
        category = next((c for c in categories if c.id == category_id), None)
        
        await state.update_data(
            user_id=user.id,
            transaction_type=transaction_type,
            amount=transaction_data["amount"],
            category_id=category_id,
            category_name=category.name,
            category_emoji=category.emoji,
            description=transaction_data.get("description"),
            recognized_text=text
        )
        
        await state.set_state(VoiceTransactionStates.waiting_confirmation)
        
        await show_voice_confirmation(processing_msg, state, edit=True)
        
    except TranscriptionError as e:
        from src.utils.sanitizer import sanitize_exception_message
        safe_error = sanitize_exception_message(e)
        logger.error(f"Ошибка транскрипции: {safe_error}")
        await processing_msg.edit_text(
            f"❌ Не удалось распознать речь: {e}\n\n"
            "Попробуйте еще раз или используйте /add"
        )
    except ParsingError as e:
        logger.error(f"Ошибка парсинга: {e}")
        await processing_msg.edit_text(
            f"❌ Ошибка обработки: {e}\n\n"
            "Попробуйте еще раз или используйте /add"
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке голоса: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке голосового сообщения.\n\n"
            "Попробуйте еще раз или используйте /add"
        )
    finally:
        if audio_path and audio_path.exists():
            try:
                os.remove(audio_path)
                logger.debug(f"Временный файл удален: {audio_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")


## Показ подтверждения голосовой транзакции
async def show_voice_confirmation(message: Message, state: FSMContext, edit: bool = False) -> None:
    """
    Показать подтверждение распознанной голосовой транзакции.
    
    :param message: Сообщение для ответа
    :param state: Контекст FSM
    :param edit: Редактировать ли существующее сообщение
    :return: None
    """
    data = await state.get_data()
    
    transaction_type = data["transaction_type"]
    amount = data["amount"]
    category_name = data["category_name"]
    category_emoji = data["category_emoji"]
    description = data.get("description")
    recognized_text = data.get("recognized_text", "")
    
    type_emoji = "💰" if transaction_type == "income" else "💸"
    type_text = "Доход" if transaction_type == "income" else "Расход"
    sign = "+" if transaction_type == "income" else "-"
    
    text = (
        f"🎤 <b>Распознано из голоса</b>\n\n"
        f"<i>«{recognized_text}»</i>\n\n"
        f"📋 <b>Данные транзакции:</b>\n"
        f"{type_emoji} <b>{type_text}</b>\n"
        f"💵 Сумма: <b>{sign}{float(amount):.2f} ₽</b>\n"
        f"{category_emoji} Категория: <b>{category_name}</b>"
    )
    
    if description:
        text += f"\n📝 Описание: {description}"
    
    text += "\n\n<i>Всё верно?</i>"
    
    if edit:
        await message.edit_text(text, reply_markup=get_voice_confirmation_keyboard())
    else:
        await message.answer(text, reply_markup=get_voice_confirmation_keyboard())


## Подтверждение голосовой транзакции
@router.callback_query(StateFilter(VoiceTransactionStates.waiting_confirmation), F.data == "voice:confirm")
async def process_voice_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка подтверждения голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    data = await state.get_data()
    
    try:
        transaction_type_str = data["transaction_type"]
        transaction_type = TransactionType.INCOME if transaction_type_str == "income" else TransactionType.EXPENSE
        
        transaction = await create_transaction(
            user_id=data["user_id"],
            transaction_type=transaction_type,
            amount=data["amount"],
            category_id=data["category_id"],
            description=data.get("description")
        )
        
        type_emoji = "💰" if transaction_type == TransactionType.INCOME else "💸"
        sign = "+" if transaction_type == TransactionType.INCOME else "-"
        
        await callback.message.edit_text(
            f"✅ <b>Транзакция сохранена!</b>\n\n"
            f"{type_emoji} {sign}{float(data['amount']):.2f} ₽\n"
            f"{data['category_emoji']} {data['category_name']}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения голосовой транзакции: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении. Попробуйте еще раз."
        )
        await state.clear()
    
    await callback.answer()


## Переход к редактированию
@router.callback_query(StateFilter(VoiceTransactionStates.waiting_confirmation), F.data == "voice:edit")
async def process_voice_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка перехода к редактированию голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    data = await state.get_data()
    
    type_emoji = "💰" if data["transaction_type"] == "income" else "💸"
    type_text = "Доход" if data["transaction_type"] == "income" else "Расход"
    sign = "+" if data["transaction_type"] == "income" else "-"
    
    text = (
        f"✏️ <b>Редактирование транзакции</b>\n\n"
        f"{type_emoji} <b>{type_text}</b>\n"
        f"💵 Сумма: <b>{sign}{float(data['amount']):.2f} ₽</b>\n"
        f"{data['category_emoji']} Категория: <b>{data['category_name']}</b>\n"
    )
    
    if data.get("description"):
        text += f"📝 Описание: {data['description']}\n"
    
    text += "\n<i>Выберите поле для редактирования:</i>"
    
    await callback.message.edit_text(text, reply_markup=get_voice_edit_keyboard())
    await callback.answer()


## Редактирование суммы
@router.callback_query(StateFilter(VoiceTransactionStates.waiting_confirmation), F.data == "voice_edit:amount")
async def process_voice_edit_amount(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало редактирования суммы голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.set_state(VoiceTransactionStates.editing_amount)
    
    await callback.message.edit_text(
        "💵 <b>Редактирование суммы</b>\n\n"
        "Введите новую сумму (только число):\n\n"
        "<i>Примеры: 500, 1500.50, 15000</i>",
        reply_markup=get_voice_edit_cancel_keyboard()
    )
    await callback.answer()


## Обработка ввода новой суммы
@router.message(StateFilter(VoiceTransactionStates.editing_amount))
async def process_voice_amount_input(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода новой суммы для голосовой транзакции.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    from decimal import Decimal, InvalidOperation
    
    amount_str = message.text.replace(",", ".").replace("₽", "").replace(" ", "")
    
    try:
        amount = Decimal(amount_str)
        
        if amount <= 0:
            await message.answer(
                "❌ Сумма должна быть положительной.\n\n"
                "Введите корректное число:",
                reply_markup=get_voice_edit_cancel_keyboard()
            )
            return
        
        if amount > 10_000_000:
            await message.answer(
                "❌ Сумма слишком большая (максимум 10 000 000).\n\n"
                "Введите корректное число:",
                reply_markup=get_voice_edit_cancel_keyboard()
            )
            return
        
        await state.update_data(amount=amount)
        await state.set_state(VoiceTransactionStates.waiting_confirmation)
        
        await show_voice_confirmation(message, state)
        
    except (ValueError, InvalidOperation):
        await message.answer(
            "❌ Некорректный формат суммы.\n\n"
            "Введите число (можно с копейками через точку):\n"
            "Примеры: 500, 1500.50",
            reply_markup=get_voice_edit_cancel_keyboard()
        )


## Редактирование категории
@router.callback_query(StateFilter(VoiceTransactionStates.waiting_confirmation), F.data == "voice_edit:category")
async def process_voice_edit_category(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало редактирования категории голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.set_state(VoiceTransactionStates.editing_category)
    
    data = await state.get_data()
    category_type = CategoryType.EXPENSE if data["transaction_type"] == "expense" else CategoryType.INCOME
    
    categories = await get_categories(
        user_id=data["user_id"],
        category_type=category_type,
        include_default=True
    )
    
    categories_list = [(cat.id, cat.name, cat.emoji) for cat in categories]
    
    type_text = "расхода" if category_type == CategoryType.EXPENSE else "дохода"
    
    await callback.message.edit_text(
        f"🏷 <b>Редактирование категории</b>\n\n"
        f"Выберите категорию {type_text}:",
        reply_markup=get_voice_categories_keyboard(categories_list, data["transaction_type"])
    )
    await callback.answer()


## Обработка выбора новой категории
@router.callback_query(StateFilter(VoiceTransactionStates.editing_category), F.data.startswith("voice_cat:"))
async def process_voice_category_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка выбора новой категории для голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    category_id = int(callback.data.split(":")[1])
    
    # Получаем информацию о категории
    data = await state.get_data()
    category_type = CategoryType.EXPENSE if data["transaction_type"] == "expense" else CategoryType.INCOME
    
    categories = await get_categories(
        user_id=data["user_id"],
        category_type=category_type,
        include_default=True
    )
    
    category = next((c for c in categories if c.id == category_id), None)
    
    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    await state.update_data(
        category_id=category.id,
        category_name=category.name,
        category_emoji=category.emoji
    )
    
    await state.set_state(VoiceTransactionStates.waiting_confirmation)
    
    await show_voice_confirmation(callback.message, state, edit=True)
    await callback.answer()


## Редактирование описания
@router.callback_query(StateFilter(VoiceTransactionStates.waiting_confirmation), F.data == "voice_edit:description")
async def process_voice_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало редактирования описания голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.set_state(VoiceTransactionStates.editing_description)
    
    data = await state.get_data()
    current_description = data.get("description", "")
    
    text = "📝 <b>Редактирование описания</b>\n\n"
    
    if current_description:
        text += f"<i>Текущее:</i> {current_description}\n\n"
    
    text += "Введите новое описание или отправьте «-» чтобы удалить:"
    
    await callback.message.edit_text(text, reply_markup=get_voice_edit_cancel_keyboard())
    await callback.answer()


## Обработка ввода нового описания
@router.message(StateFilter(VoiceTransactionStates.editing_description))
async def process_voice_description_input(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода нового описания для голосовой транзакции.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    description = message.text.strip()
    
    if description == "-":
        # Удалить описание
        await state.update_data(description=None)
    else:
        if len(description) > 500:
            await message.answer(
                "❌ Описание слишком длинное (максимум 500 символов).\n\n"
                "Введите описание:",
                reply_markup=get_voice_edit_cancel_keyboard()
            )
            return
        
        await state.update_data(description=description)
    
    await state.set_state(VoiceTransactionStates.waiting_confirmation)
    
    await show_voice_confirmation(message, state)


## Возврат к подтверждению
@router.callback_query(StateFilter(VoiceTransactionStates), F.data == "voice:back_to_confirm")
async def process_voice_back_to_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возврат к странице подтверждения голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.set_state(VoiceTransactionStates.waiting_confirmation)
    await show_voice_confirmation(callback.message, state, edit=True)
    await callback.answer()


## Возврат к меню редактирования
@router.callback_query(StateFilter(VoiceTransactionStates), F.data == "voice:back_to_edit_menu")
async def process_voice_back_to_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возврат к меню редактирования голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.set_state(VoiceTransactionStates.waiting_confirmation)
    await process_voice_edit(callback, state)


## Отмена голосовой транзакции
@router.callback_query(StateFilter(VoiceTransactionStates), F.data == "voice:cancel")
async def process_voice_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка отмены голосовой транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.clear()
    await callback.message.edit_text("❌ Транзакция отменена.")
    await callback.answer()


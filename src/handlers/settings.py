"""
Обработчики для настроек пользователя.

Управляет настройками лимитов транзакций и других параметров профиля.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from decimal import Decimal
from datetime import datetime, timezone

from src.models import get_session, User
from src.services.database import get_or_create_user, get_user_statistics
from src.states.settings_states import SettingsStates
from src.keyboards.settings_keyboards import (
    get_settings_menu_keyboard,
    get_cancel_settings_keyboard,
    get_remove_limit_keyboard
)
from sqlalchemy import select
from config import get_settings

router = Router(name="settings")


## Команда /settings
@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """
    Открыть меню настроек (команда).
    
    :param message: Сообщение от пользователя
    :return: None
    """
    user = message.from_user
    logger.info(f"Пользователь {user.id} открыл настройки")
    
    text = (
        "⚙️ <b>Настройки профиля</b>\n\n"
        "Здесь ты можешь установить лимиты для контроля расходов.\n\n"
        "💡 <b>Что это даёт?</b>\n"
        "• Контроль за крупными тратами\n"
        "• Предупреждения при превышении лимитов\n"
        "• Более осознанный подход к финансам"
    )
    
    await message.answer(
        text,
        reply_markup=get_settings_menu_keyboard(),
        parse_mode="HTML"
    )


## Главное меню настроек
@router.callback_query(F.data == "settings:menu")
async def settings_menu(callback: CallbackQuery) -> None:
    """
    Показать главное меню настроек.
    
    :param callback: Callback query от пользователя
    :return: None
    """
    user = callback.from_user
    logger.info(f"Пользователь {user.id} открыл настройки")
    
    text = (
        "⚙️ <b>Настройки профиля</b>\n\n"
        "Здесь ты можешь установить лимиты для контроля расходов.\n\n"
        "💡 <b>Что это даёт?</b>\n"
        "• Контроль за крупными тратами\n"
        "• Предупреждения при превышении лимитов\n"
        "• Более осознанный подход к финансам"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


## Просмотр текущих лимитов
@router.callback_query(F.data == "settings:view_limits")
async def view_limits(callback: CallbackQuery) -> None:
    """
    Показать текущие установленные лимиты пользователя.
    
    :param callback: Callback query от пользователя
    :return: None
    """
    user_tg = callback.from_user
    
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_tg.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка получения данных", show_alert=True)
            return
        
        settings = get_settings()
        global_limit = settings.max_transaction_amount
        
        text = "📋 <b>Твои лимиты</b>\n\n"
        
        text += "💰 <b>Лимит одной транзакции:</b>\n"
        if user.max_transaction_limit:
            text += f"└ {user.max_transaction_limit:,}₽ (персональный)\n\n"
        else:
            text += f"└ {global_limit:,}₽ (по умолчанию)\n\n"
        
        text += "📊 <b>Месячный лимит трат:</b>\n"
        if user.monthly_limit:
            text += f"└ {user.monthly_limit:,}₽\n\n"
            
            now = datetime.now(timezone.utc)
            start_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            stats = await get_user_statistics(user.id, start_date=start_month)
            
            spent = float(stats['total_expense'])
            remaining = user.monthly_limit - spent
            percent = (spent / user.monthly_limit * 100) if user.monthly_limit > 0 else 0
            
            text += f"💸 <b>Потрачено в этом месяце:</b>\n"
            text += f"└ {spent:,.0f}₽ из {user.monthly_limit:,}₽ ({percent:.1f}%)\n"
            text += f"└ Осталось: {remaining:,.0f}₽\n\n"
            
            if percent >= 100:
                text += "⚠️ <b>Лимит превышен!</b>\n\n"
            elif percent >= 80:
                text += "⚠️ <b>Внимание!</b> Скоро достигнешь лимита.\n\n"
        else:
            text += "└ Не установлен\n\n"
        
        text += "💡 Нажми на соответствующую кнопку, чтобы изменить лимиты."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


## Установка лимита транзакции
@router.callback_query(F.data == "settings:transaction_limit")
async def set_transaction_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать процесс установки лимита одной транзакции.
    
    :param callback: Callback query от пользователя
    :param state: FSM контекст
    :return: None
    """
    logger.info(f"Пользователь {callback.from_user.id} настраивает лимит транзакции")
    
    text = (
        "💰 <b>Лимит одной транзакции</b>\n\n"
        "Введи максимальную сумму для одной транзакции в рублях.\n\n"
        "При попытке добавить транзакцию больше этой суммы ты получишь предупреждение.\n\n"
        "💡 <i>Например: 50000</i>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_settings_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_for_transaction_limit)
    await callback.answer()


## Обработка ввода лимита транзакции
@router.message(SettingsStates.waiting_for_transaction_limit)
async def process_transaction_limit(message: Message, state: FSMContext) -> None:
    """
    Обработать введенный лимит транзакции.
    
    :param message: Сообщение от пользователя
    :param state: FSM контекст
    :return: None
    """
    user_tg = message.from_user
    
    try:
        limit = int(message.text.replace(" ", "").replace(",", ""))
        
        if limit <= 0:
            await message.answer(
                "❌ Лимит должен быть положительным числом. Попробуй еще раз."
            )
            return
        
        if limit > 1000000000:
            await message.answer(
                "❌ Слишком большое значение. Попробуй еще раз."
            )
            return
        
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_tg.id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.max_transaction_limit = limit
                await session.commit()
                
                logger.info(f"✅ Пользователь {user_tg.id} установил лимит транзакции: {limit}₽")
                
                text = (
                    f"✅ <b>Лимит установлен!</b>\n\n"
                    f"Максимальная сумма транзакции: {limit:,}₽\n\n"
                    f"Теперь при попытке добавить транзакцию больше этой суммы ты получишь предупреждение."
                )
                
                await message.answer(
                    text,
                    reply_markup=get_settings_menu_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Ошибка сохранения настроек")
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Некорректное значение. Введи число в рублях.\n\n"
            "💡 Например: 50000"
        )


## Установка месячного лимита
@router.callback_query(F.data == "settings:monthly_limit")
async def set_monthly_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать процесс установки месячного лимита трат.
    
    :param callback: Callback query от пользователя
    :param state: FSM контекст
    :return: None
    """
    logger.info(f"Пользователь {callback.from_user.id} настраивает месячный лимит")
    
    text = (
        "📊 <b>Месячный лимит трат</b>\n\n"
        "Введи максимальную сумму расходов на месяц в рублях.\n\n"
        "Бот будет отслеживать твои траты и предупреждать при приближении к лимиту.\n\n"
        "💡 <i>Например: 100000</i>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_settings_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_for_monthly_limit)
    await callback.answer()


## Обработка ввода месячного лимита
@router.message(SettingsStates.waiting_for_monthly_limit)
async def process_monthly_limit(message: Message, state: FSMContext) -> None:
    """
    Обработать введенный месячный лимит.
    
    :param message: Сообщение от пользователя
    :param state: FSM контекст
    :return: None
    """
    user_tg = message.from_user
    
    try:
        limit = int(message.text.replace(" ", "").replace(",", ""))
        
        if limit <= 0:
            await message.answer(
                "❌ Лимит должен быть положительным числом. Попробуй еще раз."
            )
            return
        
        if limit > 1000000000:
            await message.answer(
                "❌ Слишком большое значение. Попробуй еще раз."
            )
            return
        
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_tg.id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.monthly_limit = limit
                await session.commit()
                
                logger.info(f"✅ Пользователь {user_tg.id} установил месячный лимит: {limit}₽")
                
                text = (
                    f"✅ <b>Месячный лимит установлен!</b>\n\n"
                    f"Максимальные траты в месяц: {limit:,}₽\n\n"
                    f"Бот будет отслеживать твои расходы и уведомлять при достижении 80% и 100% лимита."
                )
                
                await message.answer(
                    text,
                    reply_markup=get_settings_menu_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Ошибка сохранения настроек")
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Некорректное значение. Введи число в рублях.\n\n"
            "💡 Например: 100000"
        )


## Удаление лимита транзакции
@router.callback_query(F.data == "settings:remove_transaction_limit")
async def remove_transaction_limit(callback: CallbackQuery) -> None:
    """
    Удалить персональный лимит транзакции.
    
    :param callback: Callback query от пользователя
    :return: None
    """
    user_tg = callback.from_user
    
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_tg.id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.max_transaction_limit = None
            await session.commit()
            
            logger.info(f"🗑 Пользователь {user_tg.id} удалил лимит транзакции")
            
            settings = get_settings()
            
            text = (
                "✅ <b>Персональный лимит удален</b>\n\n"
                f"Теперь используется лимит по умолчанию: {settings.max_transaction_amount:,}₽"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_settings_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()


## Удаление месячного лимита
@router.callback_query(F.data == "settings:remove_monthly_limit")
async def remove_monthly_limit(callback: CallbackQuery) -> None:
    """
    Удалить месячный лимит трат.
    
    :param callback: Callback query от пользователя
    :return: None
    """
    user_tg = callback.from_user
    
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_tg.id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.monthly_limit = None
            await session.commit()
            
            logger.info(f"🗑 Пользователь {user_tg.id} удалил месячный лимит")
            
            text = (
                "✅ <b>Месячный лимит удален</b>\n\n"
                "Теперь бот не будет отслеживать месячные траты."
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_settings_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()


## Отмена настройки
@router.callback_query(F.data == "settings:cancel")
async def cancel_settings(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменить изменение настроек.
    
    :param callback: Callback query от пользователя
    :param state: FSM контекст
    :return: None
    """
    await state.clear()
    
    text = "❌ Действие отменено"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard()
    )
    await callback.answer()

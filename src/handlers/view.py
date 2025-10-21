"""
Обработчики для просмотра транзакций и статистики.

Содержит handlers для:
- Главного меню
- Просмотра списка транзакций
- Удаления и редактирования транзакций
- Статистики
- Фильтрации по периодам
"""

import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.states import ViewTransactionsStates, EditTransactionStates, AddTransactionStates
from src.keyboards.view_keyboards import (
    get_main_menu_keyboard,
    get_transactions_navigation_keyboard,
    get_transaction_actions_keyboard,
    get_delete_confirmation_keyboard,
    get_period_filter_keyboard,
    get_edit_field_keyboard,
)
from src.keyboards.transaction_keyboards import get_categories_keyboard, get_cancel_keyboard
from src.services.database import (
    get_or_create_user,
    get_user_transactions_with_filters,
    count_user_transactions,
    get_transaction_by_id,
    delete_transaction,
    get_user_statistics,
    get_top_expense_categories,
    update_transaction,
    get_categories,
)
from src.models import TransactionType, CategoryType


router = Router(name="view")

# Константы
TRANSACTIONS_PER_PAGE = 10


## Команда /menu - главное меню
@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """
    Показать главное меню бота.
    
    :param message: Сообщение от пользователя
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    
    logger.info(f"Пользователь {user.id} открыл главное меню")
    
    await message.answer(
        "📋 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


## Callback главного меню
@router.callback_query(F.data == "menu:main")
async def show_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать главное меню (callback).
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.clear()
    
    await callback.message.edit_text(
        "📋 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


## Команда /stats - статистика
@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Показать статистику пользователя.
    
    :param message: Сообщение от пользователя
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    
    await show_statistics(message, user.id)


## Показать статистику (callback)
@router.callback_query(F.data == "menu:stats")
async def show_stats_callback(callback: CallbackQuery) -> None:
    """
    Показать статистику (callback).
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    await show_statistics(callback.message, user.id, edit=True)
    await callback.answer()


## Открыть настройки (callback)
@router.callback_query(F.data == "menu:settings")
async def show_settings_menu(callback: CallbackQuery) -> None:
    """
    Открыть меню настроек.
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    from src.keyboards.settings_keyboards import get_settings_menu_keyboard
    
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


## Открыть управление категориями (callback)
@router.callback_query(F.data == "menu:categories")
async def show_categories_menu(callback: CallbackQuery) -> None:
    """
    Открыть меню управления категориями.
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    from src.keyboards.category_keyboards import get_category_management_menu
    
    text = (
        "🏷️ <b>Управление категориями</b>\n\n"
        "Здесь ты можешь просматривать свои категории, "
        "создавать новые и редактировать существующие.\n\n"
        "💡 <b>Совет:</b> Создавай категории для точного учёта расходов!"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_category_management_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


## Вспомогательная функция для отображения статистики
async def show_statistics(
    message: Message,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    edit: bool = False
) -> None:
    """
    Отобразить статистику пользователя.
    
    :param message: Сообщение для ответа
    :param user_id: ID пользователя
    :param start_date: Начало периода
    :param end_date: Конец периода
    :param edit: Редактировать ли существующее сообщение
    :return: None
    """
    # Получаем статистику
    stats = await get_user_statistics(user_id, start_date, end_date)
    
    # Получаем топ категорий расходов
    top_categories = await get_top_expense_categories(user_id, start_date, end_date, limit=3)
    
    # Определяем период для заголовка
    if not start_date and not end_date:
        period_text = "за всё время"
    else:
        period_text = "за выбранный период"
    
    # Формируем текст
    balance_emoji = "💚" if stats['balance'] >= 0 else "💔"
    balance_sign = "+" if stats['balance'] >= 0 else ""
    
    text = (
        f"📊 <b>Статистика {period_text}</b>\n\n"
        f"{balance_emoji} <b>Баланс:</b> {balance_sign}{float(stats['balance']):.2f} ₽\n\n"
        f"💰 <b>Доходы:</b> +{float(stats['total_income']):.2f} ₽\n"
        f"   Операций: {stats['income_count']}\n\n"
        f"💸 <b>Расходы:</b> -{float(stats['total_expense']):.2f} ₽\n"
        f"   Операций: {stats['expense_count']}\n"
    )
    
    if top_categories:
        text += "\n🏆 <b>Топ категорий расходов:</b>\n"
        for i, cat in enumerate(top_categories, 1):
            text += f"{i}. {cat['emoji']} {cat['name']}: {float(cat['total']):.2f} ₽\n"
    
    if edit:
        await message.edit_text(text, reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(text, reply_markup=get_main_menu_keyboard())


## Просмотр всех транзакций
@router.message(Command("transactions"))
async def cmd_transactions(message: Message) -> None:
    """
    Показать все транзакции пользователя.
    
    :param message: Сообщение от пользователя
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    
    await show_transactions_list(message, user.id, page=1, transaction_type=None)


## Callback для просмотра транзакций
@router.callback_query(F.data.startswith("menu:"))
async def handle_menu_callback(callback: CallbackQuery) -> None:
    """
    Обработать выбор в главном меню.
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    action = callback.data.split(":")[1]
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    if action == "all":
        await show_transactions_list(callback.message, user.id, page=1, edit=True)
    elif action == "income":
        await show_transactions_list(
            callback.message, user.id, page=1, transaction_type=TransactionType.INCOME, edit=True
        )
    elif action == "expense":
        await show_transactions_list(
            callback.message, user.id, page=1, transaction_type=TransactionType.EXPENSE, edit=True
        )
    elif action == "period":
        await callback.message.edit_text(
            "📅 <b>Фильтр по периоду</b>\n\n"
            "Выберите период:",
            reply_markup=get_period_filter_keyboard()
        )
    elif action == "settings":
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\n"
            "Раздел в разработке. Скоро здесь появятся настройки бота!",
            reply_markup=get_main_menu_keyboard()
        )
    
    await callback.answer()


## Вспомогательная функция для отображения списка транзакций
async def show_transactions_list(
    message: Message,
    user_id: int,
    page: int = 1,
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    edit: bool = False
) -> None:
    """
    Отобразить список транзакций с пагинацией.
    
    :param message: Сообщение для ответа
    :param user_id: ID пользователя
    :param page: Номер страницы
    :param transaction_type: Фильтр по типу транзакции
    :param start_date: Начало периода
    :param end_date: Конец периода
    :param edit: Редактировать ли существующее сообщение
    :return: None
    """
    # Подсчитываем общее количество транзакций
    total_count = await count_user_transactions(
        user_id, transaction_type, start_date, end_date
    )
    
    if total_count == 0:
        text = "📝 <b>Транзакции не найдены</b>\n\n"
        if transaction_type == TransactionType.INCOME:
            text += "У вас пока нет доходов."
        elif transaction_type == TransactionType.EXPENSE:
            text += "У вас пока нет расходов."
        else:
            text += "У вас пока нет транзакций.\n\nДобавьте первую транзакцию командой /add"
        
        if edit:
            await message.edit_text(text, reply_markup=get_main_menu_keyboard())
        else:
            await message.answer(text, reply_markup=get_main_menu_keyboard())
        return
    
    # Вычисляем пагинацию
    total_pages = math.ceil(total_count / TRANSACTIONS_PER_PAGE)
    offset = (page - 1) * TRANSACTIONS_PER_PAGE
    
    # Получаем транзакции
    transactions = await get_user_transactions_with_filters(
        user_id=user_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        limit=TRANSACTIONS_PER_PAGE,
        offset=offset
    )
    
    # Формируем заголовок
    if transaction_type == TransactionType.INCOME:
        header = "💰 <b>Доходы</b>"
    elif transaction_type == TransactionType.EXPENSE:
        header = "💸 <b>Расходы</b>"
    else:
        header = "📝 <b>Все транзакции</b>"
    
    text = f"{header}\n\n"
    
    # Добавляем транзакции
    for tr in transactions:
        type_emoji = "💰" if tr.type == TransactionType.INCOME else "💸"
        sign = "+" if tr.type == TransactionType.INCOME else "-"
        
        date_str = tr.created_at.strftime("%d.%m.%Y %H:%M")
        
        text += (
            f"📅 {date_str}\n"
            f"{type_emoji} <b>{sign}{float(tr.amount):.2f} ₽</b> | {tr.category.emoji} {tr.category.name}\n"
        )
        
        if tr.description:
            text += f"💬 {tr.description}\n"
        
        text += f"🆔 ID: {tr.id}\n\n"
    
    text += f"\n📄 Страница {page} из {total_pages}"
    
    # Определяем тип для callback
    type_str = None
    if transaction_type == TransactionType.INCOME:
        type_str = "income"
    elif transaction_type == TransactionType.EXPENSE:
        type_str = "expense"
    
    keyboard = get_transactions_navigation_keyboard(page, total_pages, type_str)
    
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


## Навигация по страницам
@router.callback_query(F.data.startswith("nav:"))
async def handle_navigation(callback: CallbackQuery) -> None:
    """
    Обработать навигацию по страницам транзакций.
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    parts = callback.data.split(":")
    action = parts[1]
    
    if action == "page":
        await callback.answer()
        return
    
    page = int(parts[2])
    transaction_type = None
    
    if len(parts) > 3:
        type_str = parts[3]
        if type_str == "income":
            transaction_type = TransactionType.INCOME
        elif type_str == "expense":
            transaction_type = TransactionType.EXPENSE
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    await show_transactions_list(
        callback.message, user.id, page=page, transaction_type=transaction_type, edit=True
    )
    await callback.answer()


## Обработка фильтров по периоду
@router.callback_query(F.data.startswith("period:"))
async def handle_period_filter(callback: CallbackQuery) -> None:
    """
    Обработать выбор периода для фильтрации.
    
    :param callback: Callback от inline кнопки
    :return: None
    """
    period = callback.data.split(":")[1]
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    now = datetime.now()
    start_date = None
    end_date = now
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    elif period == "all":
        start_date = None
        end_date = None
    
    await show_transactions_list(
        callback.message, user.id, page=1, start_date=start_date, end_date=end_date, edit=True
    )
    await callback.answer()


## Удаление транзакции
@router.callback_query(F.data.startswith("delete:"))
async def handle_delete_transaction(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработать удаление транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    parts = callback.data.split(":")
    action = parts[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "❌ Удаление отменено.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
        return
    
    transaction_id = int(parts[-1])
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    if action == "confirm":
        # Подтверждено - удаляем
        success = await delete_transaction(transaction_id, user.id)
        
        if success:
            await callback.message.edit_text(
                "✅ <b>Транзакция удалена</b>",
                reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Транзакция {transaction_id} удалена пользователем {user.id}")
        else:
            await callback.message.edit_text(
                "❌ Транзакция не найдена или уже удалена.",
                reply_markup=get_main_menu_keyboard()
            )
        
        await state.clear()
    else:
        # Запрос подтверждения
        transaction = await get_transaction_by_id(transaction_id, user.id)
        
        if not transaction:
            await callback.answer("❌ Транзакция не найдена", show_alert=True)
            return
        
        type_emoji = "💰" if transaction.type == TransactionType.INCOME else "💸"
        sign = "+" if transaction.type == TransactionType.INCOME else "-"
        
        text = (
            "⚠️ <b>Подтверждение удаления</b>\n\n"
            f"{type_emoji} <b>{sign}{float(transaction.amount):.2f} ₽</b>\n"
            f"{transaction.category.emoji} {transaction.category.name}\n"
        )
        
        if transaction.description:
            text += f"💬 {transaction.description}\n"
        
        text += "\n<b>Удалить эту транзакцию?</b>"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_delete_confirmation_keyboard(transaction_id)
        )
    
    await callback.answer()


## Редактирование транзакции
@router.callback_query(F.data.startswith("edit:"))
async def handle_edit_transaction(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработать редактирование транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    parts = callback.data.split(":")
    action = parts[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "❌ Редактирование отменено.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
        return
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    if action == "field":
        # Выбор поля для редактирования
        field = parts[2]
        transaction_id = int(parts[3])
        
        transaction = await get_transaction_by_id(transaction_id, user.id)
        
        if not transaction:
            await callback.answer("❌ Транзакция не найдена", show_alert=True)
            return
        
        await state.update_data(
            transaction_id=transaction_id,
            user_id=user.id
        )
        
        if field == "amount":
            await state.set_state(EditTransactionStates.editing_amount)
            await callback.message.edit_text(
                f"💵 <b>Редактирование суммы</b>\n\n"
                f"Текущая сумма: <b>{float(transaction.amount):.2f} ₽</b>\n\n"
                f"Введите новую сумму:",
                reply_markup=get_cancel_keyboard()
            )
        elif field == "category":
            await state.set_state(EditTransactionStates.editing_category)
            
            # Получаем категории
            category_type = CategoryType.EXPENSE if transaction.type == TransactionType.EXPENSE else CategoryType.INCOME
            categories = await get_categories(
                user_id=user.id,
                category_type=category_type,
                include_default=True
            )
            
            categories_list = [(cat.id, cat.name, cat.emoji) for cat in categories]
            type_str = "expense" if transaction.type == TransactionType.EXPENSE else "income"
            
            await callback.message.edit_text(
                f"🏷 <b>Редактирование категории</b>\n\n"
                f"Текущая категория: {transaction.category.emoji} <b>{transaction.category.name}</b>\n\n"
                f"Выберите новую категорию:",
                reply_markup=get_categories_keyboard(categories_list, type_str)
            )
        elif field == "description":
            await state.set_state(EditTransactionStates.editing_description)
            
            desc_text = transaction.description if transaction.description else "<i>не указано</i>"
            
            await callback.message.edit_text(
                f"📝 <b>Редактирование описания</b>\n\n"
                f"Текущее описание: {desc_text}\n\n"
                f"Введите новое описание:",
                reply_markup=get_cancel_keyboard(skip_button=True)
            )
    else:
        # Показываем меню выбора поля
        transaction_id = int(parts[1])
        
        transaction = await get_transaction_by_id(transaction_id, user.id)
        
        if not transaction:
            await callback.answer("❌ Транзакция не найдена", show_alert=True)
            return
        
        type_emoji = "💰" if transaction.type == TransactionType.INCOME else "💸"
        sign = "+" if transaction.type == TransactionType.INCOME else "-"
        
        text = (
            "✏️ <b>Редактирование транзакции</b>\n\n"
            f"{type_emoji} <b>{sign}{float(transaction.amount):.2f} ₽</b>\n"
            f"{transaction.category.emoji} {transaction.category.name}\n"
        )
        
        if transaction.description:
            text += f"💬 {transaction.description}\n"
        
        text += "\n<b>Что хотите изменить?</b>"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_edit_field_keyboard(transaction_id)
        )
    
    await callback.answer()


## Ввод новой суммы
@router.message(StateFilter(EditTransactionStates.editing_amount))
async def process_edit_amount(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод новой суммы транзакции.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    amount_str = message.text.replace(",", ".").replace("₽", "").replace(" ", "")
    
    try:
        amount = float(amount_str)
        
        if amount <= 0:
            await message.answer(
                "❌ Сумма должна быть положительной.\n\nВведите корректное число:",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        if amount > 10_000_000:
            await message.answer(
                "❌ Сумма слишком большая.\n\nВведите корректное число:",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        data = await state.get_data()
        transaction_id = data["transaction_id"]
        user_id = data["user_id"]
        
        # Обновляем транзакцию
        transaction = await update_transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount
        )
        
        if transaction:
            await message.answer(
                f"✅ <b>Сумма обновлена</b>\n\n"
                f"Новая сумма: <b>{float(transaction.amount):.2f} ₽</b>",
                reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Сумма транзакции {transaction_id} обновлена на {amount}")
        else:
            await message.answer(
                "❌ Ошибка при обновлении транзакции.",
                reply_markup=get_main_menu_keyboard()
            )
        
        await state.clear()
        
    except (ValueError, Exception):
        await message.answer(
            "❌ Некорректный формат суммы.\n\nВведите число:",
            reply_markup=get_cancel_keyboard()
        )


## Выбор новой категории
@router.callback_query(StateFilter(EditTransactionStates.editing_category), F.data.startswith("category:"))
async def process_edit_category(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработать выбор новой категории.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    category_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    user_id = data["user_id"]
    
    # Обновляем транзакцию
    transaction = await update_transaction(
        transaction_id=transaction_id,
        user_id=user_id,
        category_id=category_id
    )
    
    if transaction:
        await callback.message.edit_text(
            f"✅ <b>Категория обновлена</b>\n\n"
            f"Новая категория: {transaction.category.emoji} <b>{transaction.category.name}</b>",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Категория транзакции {transaction_id} обновлена")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при обновлении транзакции.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()
    await callback.answer()


## Ввод нового описания
@router.message(StateFilter(EditTransactionStates.editing_description))
async def process_edit_description(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод нового описания.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer(
            "❌ Описание слишком длинное (максимум 500 символов).\n\nВведите описание:",
            reply_markup=get_cancel_keyboard(skip_button=True)
        )
        return
    
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    user_id = data["user_id"]
    
    # Обновляем транзакцию
    transaction = await update_transaction(
        transaction_id=transaction_id,
        user_id=user_id,
        description=description
    )
    
    if transaction:
        await message.answer(
            f"✅ <b>Описание обновлено</b>\n\n"
            f"Новое описание: {transaction.description}",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Описание транзакции {transaction_id} обновлено")
    else:
        await message.answer(
            "❌ Ошибка при обновлении транзакции.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()


## Пропуск описания (удаление)
@router.callback_query(StateFilter(EditTransactionStates.editing_description), F.data == "skip")
async def process_edit_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Удалить описание транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    data = await state.get_data()
    transaction_id = data["transaction_id"]
    user_id = data["user_id"]
    
    # Обновляем транзакцию (удаляем описание)
    transaction = await update_transaction(
        transaction_id=transaction_id,
        user_id=user_id,
        description=None
    )
    
    if transaction:
        await callback.message.edit_text(
            f"✅ <b>Описание удалено</b>",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Описание транзакции {transaction_id} удалено")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при обновлении транзакции.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()
    await callback.answer()


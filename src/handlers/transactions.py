"""
Обработчики для работы с транзакциями.

Содержит хендлеры для:
- Команды /add с пошаговым и быстрым вводом
- FSM для добавления транзакций
- Подтверждение и сохранение транзакций
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.states import AddTransactionStates
from src.keyboards.transaction_keyboards import (
    get_transaction_type_keyboard,
    get_categories_keyboard,
    get_confirmation_keyboard,
    get_cancel_keyboard,
)
from src.services.database import (
    get_or_create_user,
    get_categories,
    get_category_by_id,
    create_custom_category,
    create_transaction,
)
from src.models import CategoryType, TransactionType
from src.utils.validators import (
    validate_amount,
    validate_category_name,
    validate_description,
    sanitize_text,
)


router = Router(name="transactions")


## Команда /add - начало добавления транзакции
@router.message(Command("add"))
async def cmd_add_transaction(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /add для добавления транзакции.
    
    Поддерживает два режима:
    1. Пошаговый ввод: /add → выбор типа → сумма → категория → описание
    2. Быстрый ввод: /add расход 500 продукты
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    
    # Проверяем, есть ли параметры после команды
    command_args = message.text.split(maxsplit=1)
    
    if len(command_args) > 1:
        # Быстрый ввод с параметрами
        await handle_quick_add(message, state, user.id, command_args[1])
    else:
        # Пошаговый ввод
        await state.set_state(AddTransactionStates.choosing_type)
        await state.update_data(user_id=user.id)
        
        await message.answer(
            "💰 <b>Добавление транзакции</b>\n\n"
            "Выберите тип операции:",
            reply_markup=get_transaction_type_keyboard()
        )


## Быстрый ввод транзакции с парсингом параметров
async def handle_quick_add(message: Message, state: FSMContext, user_id: int, args_text: str) -> None:
    """
    Обработка быстрого ввода транзакции.
    
    Парсит строку формата: "тип сумма категория [описание]"
    Примеры: "расход 500 продукты", "доход 15000 зарплата"
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :param user_id: ID пользователя в БД
    :param args_text: Текст после команды /add
    :return: None
    """
    # Парсим параметры
    parts = args_text.split()
    
    if len(parts) < 2:
        await message.answer(
            "❌ Недостаточно параметров.\n\n"
            "Используйте формат: <code>/add тип сумма [категория] [описание]</code>\n"
            "Пример: <code>/add расход 500 продукты</code>"
        )
        return
    
    # Определяем тип операции
    type_str = parts[0].lower()
    if type_str in ["расход", "расходы", "трата", "траты", "expense"]:
        transaction_type = TransactionType.EXPENSE
        category_type = CategoryType.EXPENSE
    elif type_str in ["доход", "доходы", "заработок", "income"]:
        transaction_type = TransactionType.INCOME
        category_type = CategoryType.INCOME
    else:
        await message.answer(
            "❌ Неизвестный тип операции.\n\n"
            "Используйте: <b>доход</b> или <b>расход</b>"
        )
        return
    
    # Парсим сумму
    amount_str = parts[1].replace(",", ".").replace("₽", "").replace(" ", "")
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except (ValueError, InvalidOperation):
        await message.answer(
            "❌ Некорректная сумма.\n\n"
            "Введите положительное число.\n"
            "Примеры: 500, 1500.50, 15000"
        )
        return
    
    # Определяем категорию
    category = None
    description_parts = []
    
    if len(parts) > 2:
        category_name = parts[2].lower()
        
        # Получаем категории пользователя
        categories = await get_categories(
            user_id=user_id,
            category_type=category_type,
            include_default=True
        )
        
        # Ищем категорию по названию (частичное совпадение)
        for cat in categories:
            if category_name in cat.name.lower():
                category = cat
                break
        
        # Если категория не найдена, используем "Другое"
        if not category:
            for cat in categories:
                if cat.name == "Другое":
                    category = cat
                    # Добавляем название категории в описание
                    description_parts.append(f"Категория: {parts[2]}")
                    break
        
        # Описание - все что после категории
        if len(parts) > 3:
            description_parts.extend(parts[3:])
    else:
        # Категория не указана, используем "Другое"
        categories = await get_categories(
            user_id=user_id,
            category_type=category_type,
            include_default=True
        )
        for cat in categories:
            if cat.name == "Другое":
                category = cat
                break
    
    if not category:
        await message.answer(
            "❌ Не удалось определить категорию.\n\n"
            "Попробуйте использовать пошаговый ввод: /add"
        )
        return
    
    description = " ".join(description_parts) if description_parts else None
    
    # Создаем транзакцию
    try:
        transaction = await create_transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            category_id=category.id,
            description=description
        )
        
        type_emoji = "💰" if transaction_type == TransactionType.INCOME else "💸"
        type_text = "Доход" if transaction_type == TransactionType.INCOME else "Расход"
        sign = "+" if transaction_type == TransactionType.INCOME else "-"
        
        response = (
            f"✅ <b>Транзакция добавлена</b>\n\n"
            f"{type_emoji} <b>{type_text}</b>\n"
            f"💵 Сумма: <b>{sign}{amount:.2f} ₽</b>\n"
            f"{category.emoji} Категория: <b>{category.name}</b>"
        )
        
        if description:
            response += f"\n📝 Описание: {description}"
        
        await message.answer(response)
        
    except Exception as e:
        logger.error(f"Ошибка создания транзакции: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении транзакции. Попробуйте еще раз."
        )


## Выбор типа транзакции
@router.callback_query(StateFilter(AddTransactionStates.choosing_type), F.data.startswith("type:"))
async def process_type_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка выбора типа транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    transaction_type = callback.data.split(":")[1]
    
    await state.update_data(
        transaction_type=transaction_type,
        category_type=CategoryType.EXPENSE if transaction_type == "expense" else CategoryType.INCOME
    )
    
    await state.set_state(AddTransactionStates.entering_amount)
    
    type_emoji = "💸" if transaction_type == "expense" else "💰"
    type_text = "Расход" if transaction_type == "expense" else "Доход"
    
    await callback.message.edit_text(
        f"{type_emoji} <b>{type_text}</b>\n\n"
        f"Введите сумму (только число):\n\n"
        f"<i>Примеры: 500, 1500.50, 15000</i>",
        reply_markup=get_cancel_keyboard()
    )
    
    await callback.answer()


## Ввод суммы
@router.message(StateFilter(AddTransactionStates.entering_amount))
async def process_amount_input(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода суммы транзакции.
    
    Проверяет лимиты и предупреждает пользователя при их превышении.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    from sqlalchemy import select
    from src.models import User, get_session
    from datetime import datetime
    from config import get_settings
    
    ## Валидация суммы с использованием validators
    is_valid, amount, error_msg = validate_amount(message.text)
    
    if not is_valid:
        await message.answer(
            f"{error_msg}\n\n"
            "Введите корректное число:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    ## Проверка лимитов
    data = await state.get_data()
    transaction_type = data.get("transaction_type")
    
    if transaction_type == "expense":
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                settings = get_settings()
                
                transaction_limit = user.max_transaction_limit or settings.max_transaction_amount
                
                if amount > transaction_limit:
                    warning_text = (
                        f"⚠️ <b>Внимание!</b>\n\n"
                        f"Сумма {amount:,.0f}₽ превышает установленный лимит одной транзакции ({transaction_limit:,}₽).\n\n"
                        f"Ты уверен? Можешь продолжить или изменить сумму."
                    )
                    await message.answer(warning_text, parse_mode="HTML")
                
                if user.monthly_limit:
                    now = datetime.now()
                    start_month = datetime(now.year, now.month, 1)
                    from src.services.database import get_user_statistics
                    stats = await get_user_statistics(user.id, start_date=start_month)
                    
                    current_spent = float(stats['total_expense'])
                    new_total = current_spent + amount
                    
                    if new_total > user.monthly_limit:
                        remaining = user.monthly_limit - current_spent
                        over_limit = new_total - user.monthly_limit
                        
                        warning_text = (
                            f"🚨 <b>Превышение месячного лимита!</b>\n\n"
                            f"Потрачено в этом месяце: {current_spent:,.0f}₽\n"
                            f"Месячный лимит: {user.monthly_limit:,}₽\n"
                            f"Осталось: {remaining:,.0f}₽\n\n"
                            f"Эта транзакция превысит лимит на {over_limit:,.0f}₽"
                        )
                        await message.answer(warning_text, parse_mode="HTML")
                    elif (new_total / user.monthly_limit) >= 0.8:
                        percent = (new_total / user.monthly_limit) * 100
                        remaining = user.monthly_limit - new_total
                        
                        warning_text = (
                            f"⚠️ <b>Приближение к лимиту</b>\n\n"
                            f"После этой транзакции ты потратишь {percent:.0f}% месячного лимита.\n"
                            f"Останется: {remaining:,.0f}₽"
                        )
                        await message.answer(warning_text, parse_mode="HTML")
    
    await state.update_data(amount=amount)
    await state.set_state(AddTransactionStates.choosing_category)
    
    # Получаем данные для выбора категорий
    data = await state.get_data()
    user_id = data["user_id"]
    category_type = data["category_type"]
    
    # Загружаем категории
    categories = await get_categories(
        user_id=user_id,
        category_type=category_type,
        include_default=True
    )
    
    # Формируем список для клавиатуры (id, name, emoji)
    categories_list = [(cat.id, cat.name, cat.emoji) for cat in categories]
    
    type_emoji = "💸" if category_type == CategoryType.EXPENSE else "💰"
    type_text = "расхода" if category_type == CategoryType.EXPENSE else "дохода"
    
    await message.answer(
        f"{type_emoji} <b>Сумма: {amount:.2f} ₽</b>\n\n"
        f"Выберите категорию {type_text}:",
        reply_markup=get_categories_keyboard(categories_list, data["transaction_type"])
    )


## Выбор категории
@router.callback_query(StateFilter(AddTransactionStates.choosing_category), F.data.startswith("category:"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка выбора категории.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    category_data = callback.data.split(":")[1]
    
    if category_data == "custom":
        # Пользователь хочет ввести свою категорию
        await state.set_state(AddTransactionStates.entering_custom_category)
        
        data = await state.get_data()
        type_text = "расхода" if data["category_type"] == CategoryType.EXPENSE else "дохода"
        
        await callback.message.edit_text(
            f"✏️ <b>Своя категория</b>\n\n"
            f"Введите название категории {type_text}:",
            reply_markup=get_cancel_keyboard()
        )
    else:
        # Выбрана существующая категория
        category_id = int(category_data)
        category = await get_category_by_id(category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        await state.update_data(
            category_id=category_id,
            category_name=category.name,
            category_emoji=category.emoji
        )
        
        await state.set_state(AddTransactionStates.entering_description)
        
        await callback.message.edit_text(
            f"{category.emoji} <b>Категория: {category.name}</b>\n\n"
            f"Введите описание транзакции (опционально):",
            reply_markup=get_cancel_keyboard(skip_button=True)
        )
    
    await callback.answer()


## Ввод пользовательской категории
@router.message(StateFilter(AddTransactionStates.entering_custom_category))
async def process_custom_category_input(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода пользовательской категории.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    ## Валидация и очистка названия категории
    category_name = sanitize_text(message.text, max_length=50)
    
    is_valid, error_msg = validate_category_name(category_name)
    if not is_valid:
        await message.answer(
            f"{error_msg}\n\n"
            "Введите название:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    
    # Создаем новую категорию
    try:
        category = await create_custom_category(
            user_id=data["user_id"],
            name=category_name,
            category_type=data["category_type"],
            emoji="✏️"
        )
        
        await state.update_data(
            category_id=category.id,
            category_name=category.name,
            category_emoji=category.emoji
        )
        
        await state.set_state(AddTransactionStates.entering_description)
        
        await message.answer(
            f"{category.emoji} <b>Категория: {category.name}</b>\n\n"
            f"Введите описание транзакции (опционально):",
            reply_markup=get_cancel_keyboard(skip_button=True)
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания категории: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании категории. Попробуйте еще раз.",
            reply_markup=get_cancel_keyboard()
        )


## Ввод описания
@router.message(StateFilter(AddTransactionStates.entering_description))
async def process_description_input(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода описания транзакции.
    
    :param message: Сообщение от пользователя
    :param state: Контекст FSM
    :return: None
    """
    ## Валидация и очистка описания
    description = sanitize_text(message.text, max_length=500)
    
    is_valid, error_msg = validate_description(description)
    if not is_valid:
        await message.answer(
            f"{error_msg}\n\n"
            "Введите описание:",
            reply_markup=get_cancel_keyboard(skip_button=True)
        )
        return
    
    await state.update_data(description=description)
    
    # Показываем подтверждение
    await show_confirmation(message, state)


## Пропуск описания
@router.callback_query(StateFilter(AddTransactionStates.entering_description), F.data == "skip")
async def process_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка пропуска описания.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.update_data(description=None)
    
    # Показываем подтверждение
    await show_confirmation(callback.message, state, edit=True)
    await callback.answer()


## Показ страницы подтверждения
async def show_confirmation(message: Message, state: FSMContext, edit: bool = False) -> None:
    """
    Показать страницу подтверждения транзакции.
    
    :param message: Сообщение для ответа
    :param state: Контекст FSM
    :param edit: Редактировать ли существующее сообщение
    :return: None
    """
    await state.set_state(AddTransactionStates.confirmation)
    
    data = await state.get_data()
    
    transaction_type = data["transaction_type"]
    amount = data["amount"]
    category_name = data["category_name"]
    category_emoji = data["category_emoji"]
    description = data.get("description")
    
    type_emoji = "💰" if transaction_type == "income" else "💸"
    type_text = "Доход" if transaction_type == "income" else "Расход"
    sign = "+" if transaction_type == "income" else "-"
    
    text = (
        f"📋 <b>Подтверждение транзакции</b>\n\n"
        f"{type_emoji} <b>{type_text}</b>\n"
        f"💵 Сумма: <b>{sign}{amount:.2f} ₽</b>\n"
        f"{category_emoji} Категория: <b>{category_name}</b>"
    )
    
    if description:
        text += f"\n📝 Описание: {description}"
    
    text += "\n\n<i>Всё верно?</i>"
    
    if edit:
        await message.edit_text(text, reply_markup=get_confirmation_keyboard())
    else:
        await message.answer(text, reply_markup=get_confirmation_keyboard())


## Подтверждение транзакции
@router.callback_query(StateFilter(AddTransactionStates.confirmation), F.data.startswith("confirm:"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка подтверждения или отмены транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    action = callback.data.split(":")[1]
    
    if action == "no":
        # Отмена
        await state.clear()
        await callback.message.edit_text("❌ Транзакция отменена.")
        await callback.answer()
        return
    
    # Подтверждение - сохраняем транзакцию
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
            f"{type_emoji} {sign}{data['amount']:.2f} ₽\n"
            f"{data['category_emoji']} {data['category_name']}"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка сохранения транзакции: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении. Попробуйте еще раз."
        )
        await state.clear()
    
    await callback.answer()


## Отмена добавления транзакции
@router.callback_query(StateFilter("*"), F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработка отмены добавления транзакции.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    await state.clear()
    await callback.message.edit_text("❌ Операция отменена.")
    await callback.answer()


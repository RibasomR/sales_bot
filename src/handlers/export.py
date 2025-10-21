"""
Обработчики для экспорта данных.

Содержит handlers для:
- Команды /export
- Выбора периода экспорта
- Генерации и отправки Excel файла
"""

from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.states.export_states import ExportStates
from src.keyboards.export_keyboards import get_export_period_keyboard
from src.keyboards.view_keyboards import get_main_menu_keyboard
from src.services.database import get_or_create_user
from src.services.export_service import generate_transactions_excel, cleanup_export_file


router = Router(name="export")


## Команда /export - начало экспорта
@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /export.
    
    Начинает процесс экспорта данных. Предлагает пользователю
    выбрать период, за который нужно экспортировать транзакции.
    
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
    
    logger.info(f"Пользователь {user.id} запросил экспорт данных")
    
    await state.set_state(ExportStates.selecting_period)
    
    await message.answer(
        "📤 <b>Экспорт данных в Excel</b>\n\n"
        "Выберите период для экспорта транзакций:",
        reply_markup=get_export_period_keyboard()
    )


## Callback для экспорта из меню настроек
@router.callback_query(F.data == "menu:export")
async def show_export_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать меню экспорта (callback из главного меню).
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    logger.info(f"Пользователь {user.id} открыл меню экспорта")
    
    await state.set_state(ExportStates.selecting_period)
    
    await callback.message.edit_text(
        "📤 <b>Экспорт данных в Excel</b>\n\n"
        "Выберите период для экспорта транзакций:",
        reply_markup=get_export_period_keyboard()
    )
    await callback.answer()


## Обработка выбора периода
@router.callback_query(F.data.startswith("export:"))
async def handle_export_period(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработать выбор периода для экспорта.
    
    Генерирует Excel файл с транзакциями за выбранный период
    и отправляет его пользователю.
    
    :param callback: Callback от inline кнопки
    :param state: Контекст FSM
    :return: None
    """
    period = callback.data.split(":")[1]
    
    user = await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
    # Определяем период
    now = datetime.now()
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = now
    period_name = ""
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = "сегодня"
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_name = "вчера"
    elif period == "week":
        start_date = now - timedelta(days=7)
        period_name = "за неделю"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_name = "за месяц"
    elif period == "year":
        start_date = now - timedelta(days=365)
        period_name = "за год"
    elif period == "all":
        start_date = None
        end_date = None
        period_name = "за всё время"
    
    # Уведомляем о начале генерации
    await callback.message.edit_text(
        f"⏳ <b>Генерирую отчет {period_name}...</b>\n\n"
        "Это может занять несколько секунд."
    )
    await callback.answer()
    
    try:
        # Генерируем файл
        file_path = await generate_transactions_excel(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Отправляем файл
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption=(
                f"✅ <b>Экспорт завершен</b>\n\n"
                f"📊 Отчет по транзакциям {period_name}\n"
                f"📅 Дата формирования: {now.strftime('%d.%m.%Y %H:%M')}"
            )
        )
        
        # Показываем главное меню
        await callback.message.answer(
            "📋 <b>Что дальше?</b>",
            reply_markup=get_main_menu_keyboard()
        )
        
        logger.success(f"✅ Файл экспорта отправлен пользователю {user.id}")
        
        # Удаляем временный файл
        cleanup_export_file(file_path)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации экспорта для пользователя {user.id}: {e}")
        
        await callback.message.answer(
            "❌ <b>Ошибка при создании отчета</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=get_main_menu_keyboard()
        )
    
    finally:
        await state.clear()


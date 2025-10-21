"""
Сервисный слой для работы с базой данных.

Содержит функции для инициализации БД и предустановленных категорий.
"""

from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.models import (
    get_session,
    User,
    Category,
    CategoryType,
    Transaction,
    TransactionType,
)


## Предустановленные категории расходов
DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Продукты", "emoji": "🛒"},
    {"name": "Дом и ЖКХ", "emoji": "🏠"},
    {"name": "Транспорт", "emoji": "🚗"},
    {"name": "Здоровье", "emoji": "🏥"},
    {"name": "Одежда", "emoji": "👕"},
    {"name": "Развлечения", "emoji": "🎬"},
    {"name": "Рестораны и кафе", "emoji": "🍽"},
    {"name": "Связь и интернет", "emoji": "📱"},
    {"name": "Аптека", "emoji": "💊"},
    {"name": "Другое", "emoji": "✏️"},
]

## Предустановленные категории доходов
DEFAULT_INCOME_CATEGORIES = [
    {"name": "Зарплата", "emoji": "💼"},
    {"name": "Фриланс", "emoji": "💰"},
    {"name": "Подарок", "emoji": "🎁"},
    {"name": "Инвестиции", "emoji": "📈"},
    {"name": "Другое", "emoji": "✏️"},
]


async def initialize_default_categories() -> None:
    """
    Инициализация предустановленных категорий в базе данных.
    
    Создает системные категории для доходов и расходов, если их еще нет.
    Вызывается один раз при первом запуске приложения.
    
    :return: None
    
    Example:
        >>> await initialize_default_categories()
    """
    from src.models.base import async_session_maker
    
    if async_session_maker is None:
        raise Exception("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            existing_defaults = await session.execute(
                select(Category).where(Category.is_default == True)
            )
            
            if existing_defaults.scalars().first():
                logger.info("Предустановленные категории уже существуют")
                return
            
            logger.info("Создаю предустановленные категории...")
            
            for cat_data in DEFAULT_EXPENSE_CATEGORIES:
                category = Category(
                    name=cat_data["name"],
                    emoji=cat_data["emoji"],
                    type=CategoryType.EXPENSE,
                    is_default=True,
                    user_id=None
                )
                session.add(category)
            
            for cat_data in DEFAULT_INCOME_CATEGORIES:
                category = Category(
                    name=cat_data["name"],
                    emoji=cat_data["emoji"],
                    type=CategoryType.INCOME,
                    is_default=True,
                    user_id=None
                )
                session.add(category)
            
            await session.commit()
            logger.success(f"✅ Создано {len(DEFAULT_EXPENSE_CATEGORIES) + len(DEFAULT_INCOME_CATEGORIES)} предустановленных категорий")
        except Exception:
            await session.rollback()
            raise


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: str = "",
    last_name: Optional[str] = None
) -> User:
    """
    Получить существующего пользователя или создать нового.
    
    Ищет пользователя по telegram_id. Если пользователь не найден,
    создает новую запись в БД.
    
    :param telegram_id: ID пользователя в Telegram
    :param username: Username пользователя в Telegram (опционально)
    :param first_name: Имя пользователя
    :param last_name: Фамилия пользователя (опционально)
    :return: Объект пользователя
    
    Example:
        >>> user = await get_or_create_user(
        ...     telegram_id=123456789,
        ...     username="john_doe",
        ...     first_name="John"
        ... )
    """
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name
            await session.commit()
            logger.debug(f"Пользователь обновлен: {telegram_id}")
        else:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name or "Пользователь",
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"✅ Создан новый пользователь: {telegram_id}")
        
        return user


async def get_categories(
    user_id: Optional[int] = None,
    category_type: Optional[CategoryType] = None,
    include_default: bool = True
) -> list[Category]:
    """
    Получить список категорий.
    
    Возвращает категории с фильтрацией по пользователю и типу.
    Может включать как пользовательские, так и предустановленные категории.
    
    :param user_id: ID пользователя для фильтрации (опционально)
    :param category_type: Тип категории для фильтрации (опционально)
    :param include_default: Включить предустановленные категории
    :return: Список категорий
    
    Example:
        >>> categories = await get_categories(
        ...     user_id=1,
        ...     category_type=CategoryType.EXPENSE,
        ...     include_default=True
        ... )
    """
    async with get_session() as session:
        query = select(Category)
        
        conditions = []
        
        if include_default:
            if user_id:
                from sqlalchemy import or_
                conditions.append(
                    or_(Category.is_default == True, Category.user_id == user_id)
                )
            else:
                conditions.append(Category.is_default == True)
        elif user_id:
            conditions.append(Category.user_id == user_id)
        
        if category_type:
            conditions.append(Category.type == category_type)
        
        if conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))
        
        result = await session.execute(query.order_by(Category.is_default.desc(), Category.name))
        return list(result.scalars().all())


## Получение категории по ID
async def get_category_by_id(category_id: int) -> Optional[Category]:
    """
    Получить категорию по ID.
    
    :param category_id: ID категории
    :return: Объект категории или None если не найдена
    
    Example:
        >>> category = await get_category_by_id(1)
        >>> print(category.name)
    """
    async with get_session() as session:
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()


## Создание пользовательской категории
async def create_custom_category(
    user_id: int,
    name: str,
    category_type: CategoryType,
    emoji: str = "✏️"
) -> Category:
    """
    Создать пользовательскую категорию.
    
    :param user_id: ID пользователя
    :param name: Название категории
    :param category_type: Тип категории
    :param emoji: Эмодзи для категории
    :return: Созданная категория
    
    Example:
        >>> category = await create_custom_category(
        ...     user_id=1,
        ...     name="Подписки",
        ...     category_type=CategoryType.EXPENSE,
        ...     emoji="📱"
        ... )
    """
    async with get_session() as session:
        category = Category(
            name=name,
            emoji=emoji,
            type=category_type,
            is_default=False,
            user_id=user_id
        )
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        logger.info(f"✅ Создана пользовательская категория: {name} для пользователя {user_id}")
        
        return category


## Обновление категории
async def update_category(
    category_id: int,
    user_id: int,
    **kwargs
) -> Optional[Category]:
    """
    Обновить пользовательскую категорию.
    
    :param category_id: ID категории
    :param user_id: ID пользователя (для проверки прав)
    :param kwargs: Поля для обновления (name, emoji)
    :return: Обновленная категория или None
    
    Example:
        >>> category = await update_category(
        ...     category_id=10,
        ...     user_id=1,
        ...     name="Новое название",
        ...     emoji="🎯"
        ... )
    """
    async with get_session() as session:
        result = await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.user_id == user_id,
                Category.is_default == False
            )
        )
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Категория {category_id} не найдена или не принадлежит пользователю {user_id}")
            return None
        
        for key, value in kwargs.items():
            if hasattr(category, key) and key in ['name', 'emoji']:
                setattr(category, key, value)
        
        await session.commit()
        await session.refresh(category)
        
        logger.info(f"✏️ Обновлена категория {category_id} пользователя {user_id}")
        
        return category


## Удаление категории
async def delete_category(category_id: int, user_id: int) -> bool:
    """
    Удалить пользовательскую категорию.
    
    Проверяет, что категория не предустановленная и принадлежит пользователю.
    
    :param category_id: ID категории
    :param user_id: ID пользователя (для проверки прав)
    :return: True если удаление успешно, False если категория не найдена
    
    Example:
        >>> success = await delete_category(category_id=10, user_id=1)
    """
    async with get_session() as session:
        result = await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.user_id == user_id,
                Category.is_default == False
            )
        )
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Категория {category_id} не найдена или не может быть удалена")
            return False
        
        await session.delete(category)
        await session.commit()
        
        logger.info(f"🗑 Удалена категория {category_id} пользователя {user_id}")
        
        return True


## Подсчет транзакций в категории
async def count_category_transactions(category_id: int, user_id: int) -> int:
    """
    Подсчитать количество транзакций в категории.
    
    :param category_id: ID категории
    :param user_id: ID пользователя
    :return: Количество транзакций
    
    Example:
        >>> count = await count_category_transactions(category_id=10, user_id=1)
    """
    async with get_session() as session:
        result = await session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.category_id == category_id,
                Transaction.user_id == user_id
            )
        )
        return result.scalar() or 0


async def create_transaction(
    user_id: int,
    transaction_type: TransactionType,
    amount: float,
    category_id: int,
    description: Optional[str] = None
) -> Transaction:
    """
    Создать новую транзакцию.
    
    Добавляет новую финансовую операцию в базу данных.
    
    :param user_id: ID пользователя
    :param transaction_type: Тип транзакции (доход/расход)
    :param amount: Сумма транзакции
    :param category_id: ID категории
    :param description: Описание транзакции (опционально)
    :return: Созданная транзакция
    
    Example:
        >>> transaction = await create_transaction(
        ...     user_id=1,
        ...     transaction_type=TransactionType.EXPENSE,
        ...     amount=500.0,
        ...     category_id=1,
        ...     description="Покупка продуктов"
        ... )
    """
    async with get_session() as session:
        transaction = Transaction(
            user_id=user_id,
            type=transaction_type,
            amount=amount,
            category_id=category_id,
            description=description
        )
        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)
        
        logger.info(f"✅ Создана транзакция: {transaction_type.value} {amount}₽ для пользователя {user_id}")
        
        return transaction


async def get_user_transactions(
    user_id: int,
    transaction_type: Optional[TransactionType] = None,
    limit: int = 10,
    offset: int = 0
) -> list[Transaction]:
    """
    Получить список транзакций пользователя.
    
    Возвращает транзакции с пагинацией и опциональной фильтрацией по типу.
    Использует eager loading для связанных категорий.
    
    :param user_id: ID пользователя
    :param transaction_type: Фильтр по типу транзакции (опционально)
    :param limit: Количество записей для возврата
    :param offset: Смещение для пагинации
    :return: Список транзакций
    
    Example:
        >>> transactions = await get_user_transactions(
        ...     user_id=1,
        ...     transaction_type=TransactionType.EXPENSE,
        ...     limit=10
        ... )
    """
    async with get_session() as session:
        query = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(Transaction.user_id == user_id)
        )
        
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        
        query = query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        return list(result.scalars().all())


async def delete_transaction(transaction_id: int, user_id: int) -> bool:
    """
    Удалить транзакцию.
    
    Удаляет транзакцию, проверяя, что она принадлежит указанному пользователю.
    
    :param transaction_id: ID транзакции
    :param user_id: ID пользователя (для проверки прав)
    :return: True если удаление успешно, False если транзакция не найдена
    
    Example:
        >>> success = await delete_transaction(transaction_id=123, user_id=1)
    """
    async with get_session() as session:
        result = await session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return False
        
        await session.delete(transaction)
        await session.commit()
        
        logger.info(f"🗑 Удалена транзакция {transaction_id} пользователя {user_id}")
        
        return True


## Получение транзакции по ID
async def get_transaction_by_id(transaction_id: int, user_id: int) -> Optional[Transaction]:
    """
    Получить транзакцию по ID с проверкой прав доступа.
    
    :param transaction_id: ID транзакции
    :param user_id: ID пользователя (для проверки прав)
    :return: Объект транзакции или None
    
    Example:
        >>> transaction = await get_transaction_by_id(transaction_id=123, user_id=1)
    """
    async with get_session() as session:
        result = await session.execute(
            select(Transaction)
            .options(
                # Загружаем связанную категорию
                selectinload(Transaction.category)
            )
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        return result.scalar_one_or_none()


## Подсчет транзакций пользователя
async def count_user_transactions(
    user_id: int,
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> int:
    """
    Подсчитать количество транзакций пользователя.
    
    :param user_id: ID пользователя
    :param transaction_type: Фильтр по типу транзакции
    :param start_date: Начало периода
    :param end_date: Конец периода
    :return: Количество транзакций
    
    Example:
        >>> count = await count_user_transactions(user_id=1, transaction_type=TransactionType.EXPENSE)
    """
    async with get_session() as session:
        query = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        
        result = await session.execute(query)
        return result.scalar() or 0


## Получение транзакций с фильтрацией по периоду
async def get_user_transactions_with_filters(
    user_id: int,
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10,
    offset: int = 0
) -> list[Transaction]:
    """
    Получить транзакции с фильтрацией по периоду.
    
    :param user_id: ID пользователя
    :param transaction_type: Фильтр по типу транзакции
    :param start_date: Начало периода
    :param end_date: Конец периода
    :param limit: Количество записей
    :param offset: Смещение для пагинации
    :return: Список транзакций
    
    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(days=7)
        >>> transactions = await get_user_transactions_with_filters(
        ...     user_id=1,
        ...     start_date=start,
        ...     end_date=end
        ... )
    """
    async with get_session() as session:
        query = (
            select(Transaction)
            .options(selectinload(Transaction.category))
            .where(Transaction.user_id == user_id)
        )
        
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        
        query = query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        return list(result.scalars().all())


## Получение статистики пользователя
async def get_user_statistics(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """
    Получить статистику доходов и расходов пользователя.
    
    :param user_id: ID пользователя
    :param start_date: Начало периода
    :param end_date: Конец периода
    :return: Словарь со статистикой
    
    Example:
        >>> stats = await get_user_statistics(user_id=1)
        >>> print(stats['total_income'])
    """
    async with get_session() as session:
        # Базовый запрос
        query = select(
            Transaction.type,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).where(Transaction.user_id == user_id)
        
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        
        query = query.group_by(Transaction.type)
        
        result = await session.execute(query)
        rows = result.all()
        
        stats = {
            'total_income': Decimal('0'),
            'total_expense': Decimal('0'),
            'income_count': 0,
            'expense_count': 0,
            'balance': Decimal('0'),
        }
        
        for row in rows:
            if row.type == TransactionType.INCOME:
                stats['total_income'] = row.total or Decimal('0')
                stats['income_count'] = row.count
            elif row.type == TransactionType.EXPENSE:
                stats['total_expense'] = row.total or Decimal('0')
                stats['expense_count'] = row.count
        
        stats['balance'] = stats['total_income'] - stats['total_expense']
        
        return stats


## Получение топ категорий расходов
async def get_top_expense_categories(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 3
) -> list[dict]:
    """
    Получить топ категорий расходов пользователя.
    
    :param user_id: ID пользователя
    :param start_date: Начало периода
    :param end_date: Конец периода
    :param limit: Количество категорий
    :return: Список словарей с данными категорий
    
    Example:
        >>> top_categories = await get_top_expense_categories(user_id=1, limit=3)
        >>> for cat in top_categories:
        ...     print(f"{cat['name']}: {cat['total']} руб.")
    """
    async with get_session() as session:
        query = (
            select(
                Category.name,
                Category.emoji,
                func.sum(Transaction.amount).label('total'),
                func.count(Transaction.id).label('count')
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EXPENSE
                )
            )
        )
        
        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        
        query = (
            query.group_by(Category.id, Category.name, Category.emoji)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
        )
        
        result = await session.execute(query)
        rows = result.all()
        
        return [
            {
                'name': row.name,
                'emoji': row.emoji,
                'total': row.total,
                'count': row.count
            }
            for row in rows
        ]


## Обновление транзакции
async def update_transaction(
    transaction_id: int,
    user_id: int,
    **kwargs
) -> Optional[Transaction]:
    """
    Обновить поля транзакции.
    
    :param transaction_id: ID транзакции
    :param user_id: ID пользователя (для проверки прав)
    :param kwargs: Поля для обновления (amount, category_id, description)
    :return: Обновленная транзакция или None
    
    Example:
        >>> transaction = await update_transaction(
        ...     transaction_id=123,
        ...     user_id=1,
        ...     amount=1000.0,
        ...     description="Обновленное описание"
        ... )
    """
    async with get_session() as session:
        result = await session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
        
        for key, value in kwargs.items():
            if hasattr(transaction, key):
                setattr(transaction, key, value)
        
        await session.commit()
        await session.refresh(transaction)
        
        logger.info(f"✏️ Обновлена транзакция {transaction_id} пользователя {user_id}")
        
        return transaction


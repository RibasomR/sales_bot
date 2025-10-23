# Timezone-aware Timestamps Fix

## 📋 Описание проблемы

До этого исправления все временные метки `created_at` и `updated_at` в базе данных использовали тип `TIMESTAMP WITHOUT TIME ZONE`. Это могло приводить к проблемам:

1. **Некорректное сравнение дат** при работе с пользователями из разных часовых поясов
2. **Ошибки в агрегации** данных по периодам (день, месяц, год)
3. **Неоднозначность** при переходе на летнее/зимнее время
4. **Проблемы с репликацией** и синхронизацией данных

## ✅ Решение

### 1. Обновление модели данных

В `src/models/base.py` класс `TimestampMixin` теперь использует `DateTime(timezone=True)`:

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # ← Добавлено
        server_default=func.now(),
        nullable=False,
        comment="Дата и время создания записи"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # ← Добавлено
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Дата и время последнего обновления"
    )
```

### 2. Миграция базы данных

Создана Alembic миграция `45daad71f78d` которая:

- Конвертирует все колонки `created_at` и `updated_at` в тип `TIMESTAMP WITH TIME ZONE` (timestamptz)
- Применяется только для PostgreSQL (SQLite не поддерживает timezone)
- Включает downgrade для отката изменений

**Затронутые таблицы:**
- `users`
- `transactions`
- `categories`

### 3. Обновление кода приложения

Все места, где создаются datetime объекты для фильтрации, теперь используют timezone-aware datetime:

**До:**
```python
now = datetime.now()
start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
```

**После:**
```python
now = datetime.now(timezone.utc)
start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
```

**Обновленные файлы:**
- `src/handlers/view.py`
- `src/handlers/export.py`
- `src/handlers/transactions.py`
- `src/handlers/settings.py`

## 🚀 Применение изменений

### Локальная разработка

```bash
# Применить миграцию
alembic upgrade head

# Проверить статус
alembic current
```

### Production (Docker)

```bash
# Остановить бота
docker compose down

# Применить миграцию
docker compose up -d db
docker compose exec bot alembic upgrade head

# Запустить бота
docker compose up -d
```

### Откат (если нужно)

```bash
# Откатить последнюю миграцию
alembic downgrade -1

# Или откатить до конкретной версии
alembic downgrade 0f8ce514bbc2
```

## 🔍 Проверка

После применения миграции можно проверить типы колонок:

### PostgreSQL

```sql
SELECT 
    column_name, 
    data_type, 
    datetime_precision 
FROM information_schema.columns 
WHERE table_name IN ('users', 'transactions', 'categories')
  AND column_name IN ('created_at', 'updated_at');
```

Ожидаемый результат: `data_type = 'timestamp with time zone'`

### SQLite

SQLite не различает timezone-aware и naive timestamps на уровне БД, но Python код всё равно будет использовать timezone-aware объекты.

## 📊 Влияние на производительность

- ✅ Нет негативного влияния на производительность
- ✅ Размер данных не изменяется (timestamptz занимает столько же места)
- ✅ Индексы продолжают работать корректно
- ✅ Все существующие запросы остаются совместимыми

## 🛡️ Безопасность

- Миграция **НЕ изменяет** существующие данные, только тип колонок
- Все временные метки автоматически конвертируются PostgreSQL
- Откат миграции полностью безопасен

## 📝 Дополнительная информация

- **Миграция:** `alembic/versions/2025_10_24_0506-45daad71f78d_convert_timestamps_to_timezone_aware.py`
- **Changelog:** См. `docs/CHANGELOG.md` версия 1.2.1
- **Стандарт:** ISO 8601 с timezone UTC

## ❓ FAQ

**Q: Нужно ли обновлять существующие данные?**  
A: Нет, PostgreSQL автоматически конвертирует существующие timestamps в timestamptz.

**Q: Что будет с SQLite?**  
A: SQLite не поддерживает timezone на уровне БД, но Python код будет использовать timezone-aware datetime для консистентности.

**Q: Изменится ли формат отображения дат в боте?**  
A: Нет, для пользователей ничего не изменится. Это внутреннее изменение для корректной работы с датами.

**Q: Можно ли откатить изменения?**  
A: Да, используйте `alembic downgrade -1` для отката миграции.


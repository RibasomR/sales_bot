# 🗄️ Настройка базы данных

## Требования

- PostgreSQL 14 или выше
- Python 3.11+
- Установленные зависимости из `requirements.txt`

## Установка PostgreSQL

### Windows

1. Скачайте установщик с [официального сайта](https://www.postgresql.org/download/windows/)
2. Запустите установщик и следуйте инструкциям
3. Запомните пароль для пользователя `postgres`

### Linux

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS

```bash
brew install postgresql@14
brew services start postgresql@14
```

## Создание базы данных

### 1. Подключитесь к PostgreSQL

```bash
# Windows (через CMD)
psql -U postgres

# Linux/macOS
sudo -u postgres psql
```

### 2. Создайте базу данных и пользователя

```sql
-- Создание пользователя
CREATE USER finance_bot_user WITH PASSWORD 'your_secure_password';

-- Создание базы данных
CREATE DATABASE finance_bot OWNER finance_bot_user;

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE finance_bot TO finance_bot_user;

-- Выход
\q
```

## Настройка переменных окружения

1. Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

2. Отредактируйте `.env` файл:

```env
# Токен вашего Telegram бота (получите у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# API ключ OpenRouter (получите на openrouter.ai)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# URL подключения к PostgreSQL
# Формат: postgresql+asyncpg://username:password@host:port/database_name
DATABASE_URL=postgresql+asyncpg://finance_bot_user:your_secure_password@localhost:5432/finance_bot

# Redis (опционально, пока не используется)
REDIS_URL=redis://localhost:6379/0

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# Лимиты
MAX_TRANSACTION_AMOUNT=1000000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_PERIOD=60
```

## Применение миграций

После настройки базы данных и `.env` файла, примените миграции:

```bash
# Активируйте виртуальное окружение
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows

# Примените миграции
alembic upgrade head
```

Вы должны увидеть:

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial migration with users, categories and transactions tables
```

## Проверка подключения

Запустите бота для проверки:

```bash
python main.py
```

В логах должны появиться:

```
INFO     🚀 Запуск бота...
INFO     ✅ Конфигурация загружена успешно
INFO     ✅ База данных инициализирована
INFO     ✅ Предустановленные категории проверены
INFO     ✅ Handlers зарегистрированы
INFO     🔄 Начинаю polling...
```

## Структура базы данных

### Таблица `users`

Хранит информацию о пользователях бота.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| telegram_id | BIGINT | ID пользователя в Telegram (уникальный) |
| username | VARCHAR(255) | Username в Telegram |
| first_name | VARCHAR(255) | Имя пользователя |
| last_name | VARCHAR(255) | Фамилия пользователя |
| max_transaction_limit | INTEGER | Персональный лимит транзакции |
| created_at | TIMESTAMP | Дата создания |
| updated_at | TIMESTAMP | Дата обновления |

### Таблица `categories`

Хранит категории доходов и расходов.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| name | VARCHAR(100) | Название категории |
| type | ENUM | Тип категории (income/expense) |
| emoji | VARCHAR(10) | Эмодзи категории |
| is_default | BOOLEAN | Флаг предустановленной категории |
| user_id | INTEGER | ID пользователя (NULL для системных) |
| created_at | TIMESTAMP | Дата создания |
| updated_at | TIMESTAMP | Дата обновления |

### Таблица `transactions`

Хранит финансовые транзакции.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| user_id | INTEGER | ID пользователя |
| type | ENUM | Тип транзакции (income/expense) |
| amount | NUMERIC(15,2) | Сумма транзакции |
| category_id | INTEGER | ID категории |
| description | TEXT | Описание транзакции |
| created_at | TIMESTAMP | Дата создания |
| updated_at | TIMESTAMP | Дата обновления |

## Работа с миграциями

### Создание новой миграции

```bash
alembic revision -m "Описание изменений"
```

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Применить конкретную миграцию
alembic upgrade 001

# Применить следующую миграцию
alembic upgrade +1
```

### Откат миграций

```bash
# Откатить последнюю миграцию
alembic downgrade -1

# Откатить до конкретной миграции
alembic downgrade 001

# Откатить все миграции
alembic downgrade base
```

### Просмотр истории миграций

```bash
alembic history
alembic current
```

## Решение проблем

### Ошибка подключения к PostgreSQL

```
ConnectionRefusedError: [WinError 1225]
```

**Решение:**
- Проверьте, что PostgreSQL запущен
- Проверьте правильность DATABASE_URL в .env
- Убедитесь, что PostgreSQL слушает на порту 5432

### Ошибка аутентификации

```
FATAL: password authentication failed for user "finance_bot_user"
```

**Решение:**
- Проверьте правильность пароля в DATABASE_URL
- Убедитесь, что пользователь создан в PostgreSQL
- Проверьте права доступа в pg_hba.conf

### База данных не найдена

```
FATAL: database "finance_bot" does not exist
```

**Решение:**
- Создайте базу данных командой CREATE DATABASE
- Проверьте название базы в DATABASE_URL

## Резервное копирование

### Создание бэкапа

```bash
pg_dump -U finance_bot_user -d finance_bot > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
psql -U finance_bot_user -d finance_bot < backup_20250119_120000.sql
```

## Полезные команды psql

```sql
-- Подключение к базе
\c finance_bot

-- Список таблиц
\dt

-- Описание таблицы
\d users

-- Список пользователей
\du

-- Выполнение SQL из файла
\i path/to/file.sql

-- Экспорт результата в CSV
\copy (SELECT * FROM users) TO 'users.csv' CSV HEADER

-- Выход
\q
```


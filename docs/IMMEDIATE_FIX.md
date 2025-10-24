# 🚨 НЕМЕДЛЕННОЕ ИСПРАВЛЕНИЕ

## Текущая ситуация

Бот не может запуститься из-за ошибки:
```
DuplicateObjectError: type 'category_type' already exists
```

## РЕШЕНИЕ ПРЯМО СЕЙЧАС

### Вариант 1: Полная переустановка через Docker (РЕКОМЕНДУЕТСЯ)

Выполните на сервере:

```bash
# 1. Остановить все контейнеры проекта
docker stop finance_bot_app finance_bot_db finance_bot_redis

# 2. Удалить контейнеры
docker rm finance_bot_app finance_bot_db finance_bot_redis

# 3. Удалить volumes (узнать имена: docker volume ls)
docker volume ls | grep sales_bot
docker volume rm sales_bot_postgres_data sales_bot_redis_data sales_bot_whisper_cache

# 4. Запустить заново
cd /root/sales_bot
docker compose -f docker-compose.prod.yml up -d

# 5. Проверить логи
docker logs -f finance_bot_app
```

### Вариант 2: Быстрая очистка БД (сохранить данные)

```bash
# 1. Создать бэкап
docker exec finance_bot_db pg_dump -U finance_user finance_bot > backup_$(date +%Y%m%d).sql

# 2. Подключиться к БД и очистить
docker exec -it finance_bot_db psql -U finance_user -d finance_bot

# В psql выполнить:
DROP TYPE IF EXISTS category_type CASCADE;
DROP TYPE IF EXISTS transaction_type CASCADE;
DELETE FROM alembic_version;
\q

# 3. Перезапустить только бота
docker restart finance_bot_app

# 4. Проверить логи
docker logs -f finance_bot_app
```

### Вариант 3: Только перезапуск с очисткой миграции

```bash
# 1. Остановить бота
docker stop finance_bot_app

# 2. Очистить версию миграции в БД
docker exec -it finance_bot_db psql -U finance_user -d finance_bot -c "DELETE FROM alembic_version;"

# 3. Запустить бота
docker start finance_bot_app

# 4. Проверить логи
docker logs -f finance_bot_app
```

### Вариант 4: Полная очистка через Docker (если compose не работает)

```bash
# 1. Остановить ВСЕ контейнеры
docker stop $(docker ps -q)

# 2. Удалить контейнеры проекта
docker ps -a | grep finance_bot
docker rm finance_bot_app finance_bot_db finance_bot_redis

# 3. Удалить volumes
docker volume ls
docker volume rm $(docker volume ls -q | grep sales_bot)

# 4. Перейти в директорию и запустить
cd /root/sales_bot
docker compose -f docker-compose.prod.yml up -d
```

## Проверка успеха

После применения любого варианта:

```bash
# Проверить запущенные контейнеры
docker ps

# Проверить логи бота
docker logs finance_bot_app | tail -30

# Проверить логи БД
docker logs finance_bot_db | tail -20

# Должны увидеть:
# ✅ "Миграции применены"
# ✅ "Бот запущен"
# ✅ Нет ошибок DuplicateObjectError
```

## Полезные команды для диагностики

```bash
# Список всех контейнеров
docker ps -a

# Список volumes
docker volume ls

# Логи конкретного контейнера
docker logs finance_bot_app
docker logs finance_bot_db

# Подключение к БД
docker exec -it finance_bot_db psql -U finance_user -d finance_bot

# Перезапуск контейнера
docker restart finance_bot_app
```

## Если ничего не помогло

1. Удалите ВСЁ и начните с нуля:

```bash
# Остановить всё
docker stop $(docker ps -aq)

# Удалить всё
docker rm $(docker ps -aq)

# Удалить volumes
docker volume prune -f

# Заново запустить
cd /root/sales_bot
docker compose -f docker-compose.prod.yml up -d
```

2. Или запустите диагностику:

```bash
cd /root/sales_bot
./diagnose.sh
```

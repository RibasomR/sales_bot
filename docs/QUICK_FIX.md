# ⚡ Быстрое исправление ошибки миграции

## Проблема
```
DuplicateObjectError: type "category_type" already exists
```

## Быстрое решение (данные не важны)

### Через Docker Compose:
```bash
# 1. Остановить и удалить всё (включая volumes)
docker compose -f docker-compose.prod.yml down -v

# 2. Запустить заново
docker compose -f docker-compose.prod.yml up -d

# 3. Проверить логи
docker compose -f docker-compose.prod.yml logs -f bot
```

### Через Docker напрямую:
```bash
# 1. Остановить контейнеры
docker stop finance_bot_app finance_bot_db finance_bot_redis

# 2. Удалить контейнеры
docker rm finance_bot_app finance_bot_db finance_bot_redis

# 3. Узнать и удалить volumes
docker volume ls | grep sales_bot
docker volume rm sales_bot_postgres_data sales_bot_redis_data sales_bot_whisper_cache

# 4. Запустить заново
cd /root/sales_bot
docker compose -f docker-compose.prod.yml up -d

# 5. Проверить логи
docker logs -f finance_bot_app
```

## Если нужно сохранить данные

```bash
# 1. Создать бэкап
docker exec finance_bot_db pg_dump -U finance_user finance_bot > backup.sql

# 2. Удалить ENUM типы и очистить миграцию
docker exec -it finance_bot_db psql -U finance_user -d finance_bot << EOF
DROP TYPE IF EXISTS category_type CASCADE;
DROP TYPE IF EXISTS transaction_type CASCADE;
DELETE FROM alembic_version;
\q
EOF

# 3. Перезапустить бота
docker restart finance_bot_app

# 4. Проверить логи
docker logs -f finance_bot_app
```

## Проверка

```bash
# Статус контейнеров
docker ps

# Логи бота
docker logs -f finance_bot_app

# Логи БД
docker logs finance_bot_db | tail -20

# Healthcheck
curl http://localhost:8000/health
```

Подробнее: [migration_fix.md](migration_fix.md)


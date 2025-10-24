# 📦 Определение имен Docker Volumes

## Проблема

Docker Compose создает volumes с префиксом имени проекта. Имя проекта берется из:
1. Имени директории проекта (по умолчанию)
2. Переменной `COMPOSE_PROJECT_NAME` в `.env`
3. Флага `-p` при запуске

Например, если проект в `/root/finance_bot_app`, volumes будут:
- `finance_bot_app_postgres_data`
- `finance_bot_app_redis_data`

Если в другой директории `/root/sales_bot`, volumes будут:
- `sales_bot_postgres_data`
- `sales_bot_redis_data`

## Как узнать точные имена

### Способ 1: Список всех volumes

```bash
docker volume ls
```

Найдите volumes с `postgres_data` и `redis_data` в названии.

### Способ 2: Volumes конкретного проекта

```bash
# Из директории проекта
docker compose -f docker-compose.prod.yml config --volumes
```

### Способ 3: Inspect контейнера

```bash
# Найти контейнер PostgreSQL
docker ps -a | grep postgres

# Посмотреть его volumes
docker inspect finance_bot_db | grep -A 10 "Mounts"
```

## Удаление volumes

После того как узнали имена:

```bash
# Остановить контейнеры
docker compose -f docker-compose.prod.yml down

# Удалить volumes (замените на ваши имена)
docker volume rm YOUR_PROJECT_postgres_data YOUR_PROJECT_redis_data

# Или удалить все неиспользуемые volumes
docker volume prune
```

## Установка фиксированного имени проекта

Чтобы имена volumes были предсказуемыми, добавьте в `.env`:

```bash
COMPOSE_PROJECT_NAME=finance_bot
```

Тогда volumes всегда будут:
- `finance_bot_postgres_data`
- `finance_bot_redis_data`

Независимо от имени директории.

## Пример для вашего случая

Судя по скриншоту, ваш проект в `/root/sales_bot`, поэтому volumes:

```bash
# Список volumes
docker volume ls | grep sales_bot

# Удаление
docker volume rm sales_bot_postgres_data sales_bot_redis_data sales_bot_whisper_cache
```

Или используйте:

```bash
# Удалить все volumes проекта
docker compose -f docker-compose.prod.yml down -v
```

⚠️ **Внимание**: `-v` удалит ВСЕ данные!


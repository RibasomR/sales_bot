# 🚀 Быстрый старт на сервере

## Минимальная установка (5 минут)

### 1. Клонировать репозиторий

```bash
cd /root
git clone https://github.com/YOUR_USERNAME/finance_bot_app.git
cd finance_bot_app
```

### 2. Создать и настроить .env

```bash
cp env.example .env
nano .env
```

**Обязательно измените:**
- `BOT_TOKEN` - получите у [@BotFather](https://t.me/BotFather)
- `AGENTROUTER_API_KEY` - получите на [agentrouter.org](https://agentrouter.org)
- `POSTGRES_PASSWORD` - придумайте надежный пароль
- `REDIS_PASSWORD` - придумайте надежный пароль

### 3. Запустить

```bash
# Запуск в production режиме
docker compose -f docker-compose.prod.yml up -d

# Подождать 30 секунд для инициализации
sleep 30

# Применить миграции
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### 4. Проверить

```bash
# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Логи бота
docker compose -f docker-compose.prod.yml logs -f app
```

## Диагностика проблем

Если что-то не работает:

```bash
# Запустить автоматическую диагностику
./diagnose.sh
```

Или см. [QUICK_FIX.md](QUICK_FIX.md) для решения распространенных проблем.

## Обновление

```bash
# Остановить
docker compose -f docker-compose.prod.yml down

# Получить обновления
git pull origin main

# Пересобрать и запустить
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Применить миграции (если есть)
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## Полезные команды

```bash
# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f app

# Перезапуск бота
docker compose -f docker-compose.prod.yml restart app

# Остановка всего
docker compose -f docker-compose.prod.yml down

# Бэкап базы данных
docker exec finance_bot_db pg_dump -U finance_user finance_bot > backup_$(date +%Y%m%d).sql

# Проверка здоровья
curl http://localhost:8000/health
```

## Подробная документация

- [Deployment Guide](deployment_guide.md) - полное руководство по деплою
- [Migration Fix](migration_fix.md) - решение проблем с миграциями
- [Database Setup](database_setup.md) - настройка базы данных


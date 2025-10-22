# 🚀 Быстрый старт с Docker

Это руководство поможет вам запустить Finance Bot на своем сервере за 5 минут.

---

## ⚡ За 5 минут

### 1. Клонируйте репозиторий

```bash
git clone <your-repository-url>
cd Sales\ bot
```

### 2. Настройте переменные окружения

```bash
# Скопируйте шаблон
cp .env.template.docker .env

# Отредактируйте .env
nano .env
```

**Минимально необходимые изменения:**

```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11  # От @BotFather
POSTGRES_PASSWORD=your_strong_password_123
REDIS_PASSWORD=another_strong_password_456
```

### 3. Запустите бота

```bash
# Если установлен Make
make install

# Или через Docker Compose
docker compose build
docker compose up -d
sleep 30
docker compose exec bot alembic upgrade head
```

### 4. Проверьте работу

```bash
# Статус контейнеров
docker compose ps

# Логи бота
docker compose logs -f bot
```

✅ **Готово!** Напишите боту в Telegram: `/start`

---

## 📋 Подробная инструкция

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- 4+ GB RAM
- 10+ GB свободного места

### Установка Docker (Ubuntu/Debian)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверка
docker --version
docker compose version
```

### Настройка

#### Получение Bot Token

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

#### Получение AgentRouter API Key (опционально)

1. Зарегистрируйтесь на [AgentRouter](https://agentrouter.org/) через GitHub или Linux.do
2. Получите API ключ в [консоли](https://agentrouter.org/console/token)
3. Добавьте в `.env`

> **Примечание**: AgentRouter используется только для парсинга текста после транскрибации. Сама транскрибация происходит локально через Whisper.

#### Генерация паролей

```bash
# PostgreSQL
openssl rand -base64 32

# Redis
openssl rand -base64 32
```

### Конфигурация .env

```env
# ============ ОБЯЗАТЕЛЬНО ============
BOT_TOKEN=your_bot_token_from_botfather
POSTGRES_PASSWORD=generated_strong_password
REDIS_PASSWORD=another_generated_password

# ============ ОПЦИОНАЛЬНО ============
AGENTROUTER_API_KEY=your_agentrouter_key  # Для парсинга текста

# Whisper модель (tiny/base/small/medium/large)
WHISPER_MODEL=base  # Рекомендуется для баланса скорости/качества

# Логирование
LOG_LEVEL=INFO  # DEBUG для разработки

# Лимиты
MAX_TRANSACTION_AMOUNT=1000000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_PERIOD=60
```

### Выбор модели Whisper

| RAM | Модель | Качество | Скорость |
|-----|--------|----------|----------|
| 4 GB | `tiny` | ⭐⭐ | ⚡⚡⚡⚡ |
| 6 GB | `base` | ⭐⭐⭐ | ⚡⚡⚡ ✅ |
| 8+ GB | `small` | ⭐⭐⭐⭐ | ⚡⚡ |

### Запуск

#### Вариант 1: Make (рекомендуется)

```bash
# Первоначальная установка
make install

# Просмотр всех команд
make help

# Полезные команды
make logs-bot      # Логи бота
make ps            # Статус контейнеров
make health        # Проверка здоровья
make backup-db     # Бэкап базы данных
```

#### Вариант 2: Docker Compose

```bash
# Сборка
docker compose build

# Запуск
docker compose up -d

# Ожидание готовности
sleep 30

# Миграции
docker compose exec bot alembic upgrade head

# Логи
docker compose logs -f bot
```

#### Вариант 3: Автоматический скрипт

```bash
# Development
./deploy.sh

# Production
./deploy.sh prod
```

### Проверка работы

```bash
# 1. Статус всех контейнеров
docker compose ps
# Все должны быть в статусе "Up"

# 2. Проверка здоровья
make health
# Или вручную:
docker compose exec postgres pg_isready -U finance_user
docker compose exec redis redis-cli -a your_redis_password ping
curl http://localhost:8000/health

# 3. Проверка логов
docker compose logs --tail=50 bot
# Должно быть: "Bot started successfully"

# 4. Тест в Telegram
# Отправьте боту: /start
```

---

## 🔧 Управление

### Основные команды

```bash
# Запуск
make up
# или
docker compose up -d

# Остановка
make down
# или
docker compose down

# Перезапуск
make restart
# или
docker compose restart

# Пересборка бота после изменений
make rebuild-bot
# или
docker compose build bot && docker compose up -d bot
```

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Только бот
docker compose logs -f bot

# Последние 100 строк
docker compose logs --tail=100 bot

# С временными метками
docker compose logs -f -t bot
```

### Миграции БД

```bash
# Применить миграции
make migrate
# или
docker compose exec bot alembic upgrade head

# Создать новую миграцию
make migrate-create MSG="описание изменений"
# или
docker compose exec bot alembic revision --autogenerate -m "описание"

# Откатить последнюю миграцию
docker compose exec bot alembic downgrade -1
```

### Бэкапы

```bash
# Создать бэкап
make backup-db
# или
docker compose exec -T postgres pg_dump -U finance_user finance_bot > backup.sql

# Восстановить из бэкапа
make restore-db FILE=backup.sql
# или
docker compose exec -T postgres psql -U finance_user -d finance_bot < backup.sql
```

---

## 🚨 Решение проблем

### Бот не запускается

```bash
# Проверить логи
docker compose logs --tail=50 bot

# Проверить переменные окружения
docker compose exec bot env | grep BOT_TOKEN

# Пересоздать контейнер
docker compose up -d --force-recreate bot
```

### База данных недоступна

```bash
# Проверить статус
docker compose ps postgres

# Проверить логи
docker compose logs postgres

# Проверить подключение
docker compose exec postgres pg_isready -U finance_user
```

### Whisper не работает

```bash
# Проверить логи (первый запуск загружает модель - это нормально)
docker compose logs whisper

# Проверить API
curl http://localhost:8000/health

# Уменьшить модель если не хватает памяти
# В .env: WHISPER_MODEL=tiny
docker compose up -d --force-recreate whisper
```

### Порт занят

```bash
# Найти процесс
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :6379  # Redis
sudo lsof -i :8000  # Whisper

# Изменить порт в .env
POSTGRES_PORT=5433
```

### Полная переустановка

```bash
# ВНИМАНИЕ: Удалит все данные!

# Создайте бэкап
make backup-db

# Удалите все
docker compose down -v
docker compose down --rmi all

# Переустановка
make install
```

---

## 📊 Мониторинг

### Использование ресурсов

```bash
# Реальное время
docker stats

# Дисковое пространство
docker system df

# Детали контейнера
docker inspect finance_bot_app
```

### Автоматический мониторинг

Настройте мониторинг через systemd:

```bash
sudo nano /etc/systemd/system/finance-bot.service
```

```ini
[Unit]
Description=Finance Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/finance-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
```

---

## 🎯 Production деплой

### Checklist перед деплоем

- [ ] Надежные пароли в `.env`
- [ ] `BOT_TOKEN` получен от @BotFather
- [ ] Firewall настроен (только SSH открыт)
- [ ] Автозапуск через systemd настроен
- [ ] Автоматические бэкапы через cron
- [ ] Ротация логов настроена
- [ ] Monitoring настроен

### Production запуск

```bash
# Использование production конфигурации
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
# или
make up-prod
```

### Мониторинг в продакшене

```bash
# Статус
sudo systemctl status finance-bot

# Логи
sudo journalctl -u finance-bot -f

# Docker статус
docker compose ps

# Здоровье сервисов
make health
```

---

## 📚 Дополнительные ресурсы

- [Полная документация по Docker](README.Docker.md)
- [Руководство по деплою](docs/deployment_guide.md)
- [Архитектура системы](docs/docker_architecture.md)
- [Changelog](docs/CHANGELOG.md)

---

## 🆘 Поддержка

Проблемы? Проверьте:

1. Логи: `make logs-bot`
2. Здоровье: `make health`
3. [Решение проблем](README.Docker.md#-решение-проблем)
4. Создайте issue в репозитории

---

**Удачного использования! 💰**



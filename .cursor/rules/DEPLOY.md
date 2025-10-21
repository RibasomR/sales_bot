# 🚀 Быстрый деплой Finance Bot

## За 5 минут

### 1️⃣ Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Клонирование проекта
git clone <your-repo-url> /opt/finance-bot
cd /opt/finance-bot
```

### 2️⃣ Настройка

```bash
# Копирование .env
cp .env.template.docker .env
nano .env
```

**Обязательно измените:**
```env
BOT_TOKEN=your_bot_token_from_@BotFather
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
```

### 3️⃣ Запуск

```bash
# Автоматический деплой
./deploy.sh prod

# Или через Make
make install

# Или вручную
docker compose build
docker compose up -d
sleep 30
docker compose exec bot alembic upgrade head
```

### 4️⃣ Проверка

```bash
docker compose ps          # Статус контейнеров
docker compose logs -f bot # Логи бота
make health               # Проверка здоровья
```

---

## 📋 Требования

- **CPU**: 2+ ядра
- **RAM**: 4+ GB (6+ GB для модели Whisper `base`)
- **Диск**: 10+ GB
- **ОС**: Ubuntu 20.04+ / Debian 11+

---

## ⚙️ Конфигурация

### Модель Whisper

| RAM | Модель | Качество |
|-----|--------|----------|
| 4 GB | `tiny` | Базовое |
| 6 GB | `base` | Хорошее ✅ |
| 8+ GB | `small` | Отличное |

```env
WHISPER_MODEL=base  # Рекомендуется
```

### Получение Bot Token

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Скопируйте токен в `.env`

---

## 🎛️ Управление

```bash
# Запуск/остановка
make up          # Запустить
make down        # Остановить
make restart     # Перезапустить
make rebuild-bot # Пересобрать бота

# Логи
make logs        # Все логи
make logs-bot    # Только бот
make logs-whisper # Whisper API

# База данных
make migrate     # Применить миграции
make backup-db   # Создать бэкап
make restore-db FILE=backup.sql # Восстановить

# Мониторинг
make ps          # Статус контейнеров
make health      # Проверка здоровья
docker stats     # Использование ресурсов
```

---

## 🔧 Production настройка

### Автозапуск (systemd)

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
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
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

### Автоматические бэкапы (cron)

```bash
crontab -e
```

```cron
# Бэкап каждый день в 3:00
0 3 * * * cd /opt/finance-bot && make backup-db
```

### Ротация логов

```bash
sudo nano /etc/logrotate.d/finance-bot
```

```
/opt/finance-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 🚨 Решение проблем

### Бот не запускается

```bash
# Проверить логи
docker compose logs --tail=50 bot

# Проверить токен
docker compose exec bot env | grep BOT_TOKEN

# Пересоздать контейнер
docker compose up -d --force-recreate bot
```

### База данных недоступна

```bash
# Проверить статус
docker compose ps postgres

# Проверить подключение
docker compose exec postgres pg_isready -U finance_user

# Пересоздать
docker compose up -d --force-recreate postgres
```

### Whisper не работает

```bash
# Проверить логи (первый запуск загружает модель)
docker compose logs whisper

# Проверить API
curl http://localhost:8000/health

# Уменьшить модель
# В .env: WHISPER_MODEL=tiny
docker compose up -d --force-recreate whisper
```

### Недостаточно памяти

```bash
# Проверить использование
docker stats

# Создать swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Полная переустановка

```bash
# ВНИМАНИЕ: Удалит все данные!
make backup-db                    # Создать бэкап
docker compose down -v            # Удалить контейнеры и volumes
docker compose down --rmi all     # Удалить образы
make install                      # Переустановить
```

---

## 📊 Архитектура

```
┌─────────────────────────────────────────┐
│         Finance Bot Network             │
│  ┌────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Bot   │──│PostgreSQL│  │  Redis  │ │
│  │(Python)│  │          │  │         │ │
│  └────┬───┘  └──────────┘  └─────────┘ │
│       │                                 │
│  ┌────▼────┐                           │
│  │ Whisper │                           │
│  │   API   │                           │
│  └─────────┘                           │
└─────────────────────────────────────────┘
```

**Сервисы:**
- **bot** - Telegram бот (aiogram)
- **postgres** - База данных
- **redis** - Кеширование, rate limiting
- **whisper** - Локальная транскрибация голоса

---

## 📚 Дополнительная документация

- **Полная документация**: `.cursor/rules/README.Docker.md`
- **Архитектура**: Описана в docker-compose.yml
- **Roadmap**: `docs/roadmap.md`
- **Changelog**: `docs/CHANGELOG.md`

---

## ✅ Checklist после деплоя

- [ ] Все контейнеры запущены (`docker compose ps`)
- [ ] Миграции применены
- [ ] Бот отвечает в Telegram (`/start`)
- [ ] Голосовые сообщения работают
- [ ] Автозапуск настроен (systemd)
- [ ] Бэкапы настроены (cron)
- [ ] Ротация логов настроена
- [ ] Пароли изменены с дефолтных

---

## 🆘 Поддержка

**Проблемы?**
1. Проверьте логи: `make logs-bot`
2. Проверьте здоровье: `make health`
3. Изучите раздел "Решение проблем"
4. Создайте issue в репозитории

---

**Готово! Бот работает 🎉**

Напишите боту в Telegram: `/start`


# 🚀 Deployment Guide

## Минимальные требования

- **CPU**: 2 ядра (рекомендуется 4)
- **RAM**: 2 GB (рекомендуется 4 GB)
- **Диск**: 10 GB

---

## 1. Установка Docker

```bash
# Установка Docker и Docker Compose
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git curl

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверка
docker --version
docker compose version
```

---

## 2. Настройка проекта

```bash
# Клонирование
git clone <your-repo-url> ~/finance-bot
cd ~/finance-bot

# Настройка .env
cp env.example .env
nano .env
```

**Обязательно измените:**
- `BOT_TOKEN` - получите у @BotFather
- `AGENTROUTER_API_KEY` - получите на https://agentrouter.org/console/token
- `POSTGRES_PASSWORD` - придумайте надежный пароль
- `REDIS_PASSWORD` - придумайте надежный пароль

**Генерация паролей:**
```bash
openssl rand -base64 32
```

---

## 3. Запуск

```bash
# Автоматический деплой
./deploy.sh

# Или вручную
docker compose build
docker compose up -d
sleep 30
docker compose exec bot alembic upgrade head
```

**Production режим:**
```bash
./deploy.sh prod
```

---

## 4. Проверка

```bash
# Статус контейнеров
docker compose ps

# Логи бота
docker compose logs -f bot

# Healthcheck
make health
```

---

## 5. Обслуживание

### Бэкапы

```bash
# Создать бэкап
make backup-db

# Автоматические бэкапы (cron)
crontab -e
# Добавить: 0 3 * * * cd ~/finance-bot && make backup-db
```

### Обновление

```bash
git pull origin main
make rebuild-bot
```

### Автозапуск

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
WorkingDirectory=/home/YOUR_USERNAME/finance-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
```

---

## 6. Решение проблем

### Нет места на диске

```bash
docker system prune -a --volumes -f
sudo journalctl --vacuum-time=7d
sudo apt-get clean && sudo apt-get autoremove -y
```

### Бот не запускается

```bash
# Проверить логи
docker compose logs --tail=50 bot

# Проверить .env
docker compose exec bot env | grep BOT_TOKEN
```

### Redis недоступен

Бот автоматически переключится на in-memory fallback. Для продакшена рекомендуется использовать Redis.

```bash
# Проверить Redis
docker compose exec redis redis-cli ping
```

### Недостаточно памяти

Уменьшите модель Whisper в `.env`:
```env
WHISPER_MODEL=tiny
WHISPER_THREADS=2
```


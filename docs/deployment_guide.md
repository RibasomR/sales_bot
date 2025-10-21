# 🚀 Руководство по деплою Finance Bot

## 📋 Содержание

1. [Подготовка сервера](#1-подготовка-сервера)
2. [Установка зависимостей](#2-установка-зависимостей)
3. [Настройка окружения](#3-настройка-окружения)
4. [Деплой приложения](#4-деплой-приложения)
5. [Мониторинг и обслуживание](#5-мониторинг-и-обслуживание)
6. [Решение проблем](#6-решение-проблем)

---

## 1. Подготовка сервера

### Минимальные требования

- **CPU**: 2 ядра (рекомендуется 4)
- **RAM**: 4 GB (рекомендуется 8 GB для Whisper)
- **Диск**: 10 GB свободного места
- **ОС**: Ubuntu 20.04+, Debian 11+

### Первоначальная настройка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых утилит
sudo apt install -y git curl wget nano htop

# Настройка firewall (UFW)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (опционально)
sudo ufw allow 443/tcp     # HTTPS (опционально)
sudo ufw enable
sudo ufw status
```

### Создание пользователя для бота

```bash
# Создание пользователя
sudo useradd -m -s /bin/bash botuser
sudo usermod -aG sudo botuser

# Переключение на пользователя
sudo su - botuser
```

---

## 2. Установка зависимостей

### Установка Docker

```bash
# Удаление старых версий (если есть)
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt update
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавление официального GPG ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Применение изменений (перелогиньтесь)
newgrp docker

# Проверка установки
docker --version
docker compose version
```

### Установка Make (опционально)

```bash
sudo apt install -y make
```

---

## 3. Настройка окружения

### Клонирование репозитория

```bash
# Создание директории для проекта
sudo mkdir -p /opt/finance-bot
sudo chown $USER:$USER /opt/finance-bot
cd /opt/finance-bot

# Клонирование репозитория
git clone <your-repository-url> .

# Или загрузка через SCP/SFTP
```

### Настройка переменных окружения

```bash
# Копирование шаблона
cp .env.template.docker .env

# Редактирование .env
nano .env
```

**Обязательные параметры для изменения:**

```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# OpenRouter API Key (для парсинга текста)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx

# PostgreSQL пароль (сгенерировать надежный пароль)
POSTGRES_PASSWORD=strong_unique_password_123

# Redis пароль (сгенерировать надежный пароль)
REDIS_PASSWORD=another_strong_password_456
```

**Генерация надежных паролей:**

```bash
# Генерация случайного пароля
openssl rand -base64 32
```

### Настройка модели Whisper

В зависимости от ресурсов сервера:

| RAM сервера | Рекомендуемая модель | Производительность |
|-------------|---------------------|-------------------|
| 4 GB | `tiny` | Быстро, базовое качество |
| 6 GB | `base` | Средне, хорошее качество ✅ |
| 8+ GB | `small` | Медленно, отличное качество |

```env
# В .env
WHISPER_MODEL=base  # tiny, base, small, medium, large
WHISPER_DEVICE=cpu  # Или cuda, если есть GPU
```

---

## 4. Деплой приложения

### Метод 1: Автоматический деплой (рекомендуется)

```bash
# Использование скрипта деплоя
./deploy.sh

# Или для production режима
./deploy.sh prod
```

### Метод 2: С использованием Makefile

```bash
# Первоначальная установка
make install

# Или пошагово:
make build      # Сборка образов
make up         # Запуск сервисов
sleep 30        # Ожидание готовности
make migrate    # Применение миграций
```

### Метод 3: Вручную через docker-compose

```bash
# Сборка образов
docker compose build

# Запуск сервисов
docker compose up -d

# Ожидание готовности
sleep 30

# Применение миграций
docker compose exec bot alembic upgrade head

# Проверка статуса
docker compose ps
```

### Production деплой

Для продакшен окружения используйте оптимизированную конфигурацию:

```bash
# Запуск в production режиме
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Отличия production режима:**

- Ограничение ресурсов для контейнеров
- Политика перезапуска при сбоях
- Ротация логов
- Порты не экспонируются наружу

---

## 5. Мониторинг и обслуживание

### Проверка статуса

```bash
# Статус контейнеров
docker compose ps
make ps

# Проверка здоровья сервисов
make health

# Использование ресурсов
docker stats
```

### Просмотр логов

```bash
# Все логи
docker compose logs -f

# Только бот
docker compose logs -f bot
make logs-bot

# Последние 100 строк
docker compose logs --tail=100 bot

# Логи за период
docker compose logs --since 2025-01-20T10:00:00 bot
```

### Регулярное обслуживание

#### Создание бэкапов

```bash
# Бэкап базы данных
make backup-db

# Или вручную
docker compose exec -T postgres pg_dump -U finance_user finance_bot > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Настройка автоматических бэкапов (cron):**

```bash
# Редактировать crontab
crontab -e

# Добавить задачу (бэкап каждый день в 3:00)
0 3 * * * cd /opt/finance-bot && /usr/bin/make backup-db >> /var/log/finance-bot-backup.log 2>&1
```

#### Очистка логов

```bash
# Очистка Docker логов
docker compose logs --tail=0 > /dev/null

# Настройка logrotate
sudo nano /etc/logrotate.d/finance-bot
```

Содержимое `/etc/logrotate.d/finance-bot`:

```
/opt/finance-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 botuser botuser
}
```

#### Обновление приложения

```bash
# Получение обновлений из репозитория
git pull origin main

# Пересборка и перезапуск
make rebuild-bot

# Или полная пересборка
docker compose down
docker compose build --no-cache
docker compose up -d
make migrate
```

### Настройка автозапуска

Создайте systemd service для автоматического запуска при перезагрузке сервера.

**Создание файла сервиса:**

```bash
sudo nano /etc/systemd/system/finance-bot.service
```

**Содержимое файла:**

```ini
[Unit]
Description=Finance Bot Docker Compose Service
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/finance-bot
User=botuser
Group=botuser

# Для production
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose down

# Для development
# ExecStart=/usr/bin/docker compose up -d
# ExecStop=/usr/bin/docker compose down

TimeoutStartSec=300
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable finance-bot

# Запуск сервиса
sudo systemctl start finance-bot

# Проверка статуса
sudo systemctl status finance-bot

# Просмотр логов systemd
sudo journalctl -u finance-bot -f
```

**Управление сервисом:**

```bash
sudo systemctl start finance-bot    # Запуск
sudo systemctl stop finance-bot     # Остановка
sudo systemctl restart finance-bot  # Перезапуск
sudo systemctl status finance-bot   # Статус
```

---

## 6. Решение проблем

### Бот не запускается

**Проблема**: Контейнер бота постоянно перезапускается

```bash
# Проверить логи
docker compose logs --tail=50 bot

# Проверить переменные окружения
docker compose exec bot env | grep BOT_TOKEN

# Проверить подключение к БД
docker compose exec bot python -c "from config.config import DATABASE_URL; print(DATABASE_URL)"
```

**Решение**:
- Проверьте правильность `BOT_TOKEN` в `.env`
- Убедитесь, что БД запущена: `docker compose ps postgres`
- Проверьте доступность сети: `docker network ls`

### Whisper не транскрибирует

**Проблема**: Ошибки при обработке голосовых сообщений

```bash
# Проверить статус Whisper
docker compose ps whisper

# Проверить логи
docker compose logs --tail=50 whisper

# Проверить API
curl http://localhost:8000/health

# Войти в контейнер
docker compose exec whisper /bin/bash
```

**Решение**:
- Модель Whisper загружается при первом запуске, это может занять время
- Если не хватает памяти, уменьшите модель: `WHISPER_MODEL=tiny`
- Проверьте доступность ffmpeg в контейнере

### База данных недоступна

**Проблема**: Ошибки подключения к PostgreSQL

```bash
# Проверить статус PostgreSQL
docker compose ps postgres

# Проверить логи
docker compose logs postgres

# Проверить подключение
docker compose exec postgres pg_isready -U finance_user

# Войти в psql
docker compose exec postgres psql -U finance_user -d finance_bot
```

**Решение**:
- Проверьте правильность пароля в `.env`
- Убедитесь, что volume не поврежден
- При необходимости пересоздайте контейнер: `docker compose up -d --force-recreate postgres`

### Недостаточно памяти

**Проблема**: Сервер зависает или контейнеры убиваются OOM killer

```bash
# Проверить использование памяти
docker stats

# Проверить системную память
free -h

# Проверить swap
swapon --show
```

**Решение**:

1. Уменьшить модель Whisper:
```env
WHISPER_MODEL=tiny
```

2. Создать swap файл (если нет):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

3. Ограничить ресурсы в production режиме (уже настроено в `docker-compose.prod.yml`)

### Миграции не применяются

**Проблема**: Ошибки при `alembic upgrade head`

```bash
# Проверить текущую версию
docker compose exec bot alembic current

# Проверить доступные миграции
docker compose exec bot alembic history

# Откатить миграцию
docker compose exec bot alembic downgrade -1

# Применить заново
docker compose exec bot alembic upgrade head
```

**Решение**:
- Убедитесь, что БД доступна и содержит схему
- Проверьте файлы миграций в `alembic/versions/`
- При необходимости откатите и примените заново

### Порты заняты

**Проблема**: Ошибка "port is already allocated"

```bash
# Найти процессы на портах
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :6379  # Redis
sudo lsof -i :8000  # Whisper

# Или через netstat
sudo netstat -tulpn | grep :5432
```

**Решение**:

1. Остановите конфликтующие сервисы
2. Или измените порты в `.env`:
```env
POSTGRES_PORT=5433
REDIS_PORT=6380
WHISPER_PORT=8001
```

### Полная переустановка

Если ничего не помогает:

```bash
# ВНИМАНИЕ: Это удалит все данные!

# Создайте бэкап перед удалением
make backup-db

# Остановка и удаление контейнеров и volumes
docker compose down -v

# Удаление образов
docker compose down --rmi all

# Очистка системы Docker
docker system prune -a --volumes

# Переустановка
make install
```

---

## 📞 Поддержка

При возникновении проблем:

1. Изучите логи: `make logs-bot`
2. Проверьте здоровье: `make health`
3. Проверьте этот раздел документации
4. Создайте issue в репозитории

---

## ✅ Чеклист после деплоя

- [ ] Все контейнеры запущены (`docker compose ps`)
- [ ] Миграции применены успешно
- [ ] Бот отвечает в Telegram
- [ ] Голосовые сообщения обрабатываются
- [ ] Настроен автозапуск (systemd)
- [ ] Настроены автоматические бэкапы (cron)
- [ ] Настроена ротация логов (logrotate)
- [ ] Firewall настроен корректно
- [ ] Пароли в `.env` изменены с дефолтных
- [ ] Мониторинг настроен

---

**Успешного деплоя! 🎉**



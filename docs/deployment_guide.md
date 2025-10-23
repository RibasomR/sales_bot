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

- **CPU**: 2 ядра (рекомендуется 4 для Whisper.cpp)
- **RAM**: 2 GB (рекомендуется 4 GB, Whisper.cpp использует на 75% меньше памяти)
- **Диск**: 10 GB свободного места
- **ОС**: Ubuntu 20.04+, Debian 11+

> ⚡ **Whisper.cpp**: Проект использует оптимизированную версию Whisper, которая работает в 2-4 раза быстрее и потребляет в 4 раза меньше памяти чем openai-whisper.

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

---

## 2. Установка зависимостей

### Установка Docker

```bash
# Удаление старых версий (если есть)
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
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
sudo apt update

---

## 3. Настройка окружения

### Клонирование репозитория

```bash
# Создание директории для проекта (или используйте домашнюю директорию)
mkdir -p ~/finance-bot
cd ~/finance-bot

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

# AgentRouter API Key (для парсинга текста)
AGENTROUTER_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

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

### Настройка модели Whisper.cpp

В зависимости от ресурсов сервера:

| RAM сервера | Рекомендуемая модель | CPU потоки | Производительность |
|-------------|---------------------|------------|-------------------|
| 2 GB | `tiny` | 2 | Очень быстро, базовое качество |
| 4 GB | `base` ✅ | 4 | Быстро, хорошее качество |
| 6+ GB | `small` | 4-6 | Средне, отличное качество |
| 8+ GB | `medium` | 6-8 | Медленно, превосходное качество |

```env
# В .env
WHISPER_MODEL=base      # tiny, base, small, medium, large
WHISPER_THREADS=4       # Количество CPU потоков (2-8)
```

> **Примечание:** Whisper.cpp не поддерживает GPU, но CPU версия работает быстрее старой GPU версии openai-whisper благодаря оптимизациям.

---

## 4. Деплой приложения

### Метод 1: Автоматический деплой (рекомендуется)

```bash
# Использование скрипта деплоя
./deploy.sh

# Или для production режима
./deploy.sh prod
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
0 3 * * * cd ~/finance-bot && /usr/bin/make backup-db >> ~/finance-bot-backup.log 2>&1
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
/home/YOUR_USERNAME/finance-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 YOUR_USERNAME YOUR_USERNAME
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
WorkingDirectory=/home/YOUR_USERNAME/finance-bot

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

## 6. Очистка места на диске

### Если закончилось место во время сборки Docker

#### ⚠️ Ошибка: "No space left on device"

Если при сборке Docker образа появляется ошибка `dpkg: error processing archive ... failed to write (No space left on device)`, выполните следующие действия:

```bash
# 1. Проверьте доступное место
df -h

# 2. Остановите и удалите все контейнеры
docker stop $(docker ps -aq) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null

# 3. Удалите неиспользуемые образы
docker image prune -a -f

# 4. Удалите неиспользуемые volumes
docker volume prune -f

# 5. Удалите build cache
docker builder prune -a -f

# 6. Полная очистка Docker (ВНИМАНИЕ: удалит ВСЁ)
docker system prune -a --volumes -f

# 7. Проверьте освободившееся место
df -h

# 8. Очистите системные логи (освободит 1-2 GB)
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=100M

# 9. Очистите APT кэш
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove -y

# 10. Удалите старые ядра Linux (если есть)
sudo apt-get autoremove --purge -y

# 11. Проверьте итоговое место
df -h
```

#### После очистки пересоберите образ:

```bash
cd ~/finance-bot
docker compose build --no-cache
docker compose up -d
```

### Мониторинг использования диска

```bash
# Показать использование по директориям
du -sh /*

# Найти большие файлы (>100MB)
find / -type f -size +100M 2>/dev/null

# Проверка места Docker
docker system df
```

---

## 7. Решение проблем

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

### Whisper.cpp не транскрибирует

**Проблема**: Ошибки при обработке голосовых сообщений

```bash
# Проверить статус Whisper.cpp
docker compose ps whisper

# Проверить логи
docker compose logs --tail=50 whisper

# Проверить API (должен показать backend: whisper.cpp)
curl http://localhost:8000/health

# Ожидаемый ответ:
# {
#   "status": "healthy",
#   "model": "base",
#   "backend": "whisper.cpp",
#   "threads": 4
# }

# Войти в контейнер
docker compose exec whisper /bin/bash
```

**Решение**:
- Модель Whisper.cpp (GGML формат) загружается автоматически при первом запуске (~150MB)
- Если не хватает памяти, уменьшите модель и количество потоков:
  ```env
  WHISPER_MODEL=tiny
  WHISPER_THREADS=2
  ```
- Проверьте доступность ffmpeg в контейнере
- Whisper.cpp требует build-essential для компиляции (уже включено в Dockerfile)
- Первая транскрипция может занять больше времени (загрузка модели)

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

1. Уменьшить модель Whisper.cpp и количество потоков:
```env
WHISPER_MODEL=tiny
WHISPER_THREADS=2
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
sudo lsof -i :8000  # Whisper.cpp

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

### Миграция с openai-whisper на Whisper.cpp

**Если вы обновляете существующую установку:**

```bash
# 1. Остановите сервисы
docker compose down

# 2. Обновите .env файл
nano .env

# Удалите (если есть):
# WHISPER_DEVICE=cpu

# Добавьте:
WHISPER_MODEL=base
WHISPER_THREADS=4

# 3. Получите последние изменения
git pull origin main

# 4. Пересоберите Whisper контейнер
docker compose build --no-cache whisper

# 5. Запустите сервисы
docker compose up -d

# 6. Проверьте, что используется whisper.cpp
curl http://localhost:8000/health
# Должно показать: "backend": "whisper.cpp"
```

**Преимущества после миграции:**
- ⚡ Скорость транскрибации: **2-4x быстрее**
- 💾 Использование RAM: **-75%** (2GB → 500MB)
- 📦 Размер Docker образа: **-75%** (4GB → 1GB)
- ✅ Точность: **без изменений**

Подробнее: см. [MIGRATION_TO_WHISPER_CPP.md](MIGRATION_TO_WHISPER_CPP.md)

---

## 📞 Поддержка

При возникновении проблем:

1. Изучите логи: `make logs-bot`
2. Проверьте здоровье: `make health`
3. Проверьте этот раздел документации
4. Создайте issue в репозитории

---

## ✅ Чеклист после деплоя

### Базовая проверка
- [ ] Все контейнеры запущены (`docker compose ps`)
- [ ] Миграции применены успешно
- [ ] Бот отвечает в Telegram (`/start`)
- [ ] Ручное добавление транзакций работает (`/add`)

### Whisper.cpp проверка
- [ ] Whisper.cpp API доступен (`curl http://localhost:8000/health`)
- [ ] API возвращает `"backend": "whisper.cpp"`
- [ ] Голосовые сообщения транскрибируются корректно
- [ ] Время транскрибации приемлемое (обычно 2-5 секунд для 5-сек аудио)

### Безопасность и обслуживание
- [ ] Пароли в `.env` изменены с дефолтных
- [ ] Firewall настроен корректно (`sudo ufw status`)
- [ ] Настроен автозапуск (systemd service)
- [ ] Настроены автоматические бэкапы (cron)
- [ ] Настроена ротация логов (logrotate)
- [ ] Мониторинг настроен (`make health`)

### Производительность
- [ ] Использование памяти в норме (`docker stats`)
- [ ] Нет перезапусков контейнеров (`docker compose ps`)
- [ ] Логи без критических ошибок (`make logs-bot`)

---

**Успешного деплоя! 🎉**



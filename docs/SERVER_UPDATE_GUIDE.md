# 🚀 Инструкция по обновлению бота на сервере

## Быстрое обновление (рекомендуется)

### Шаг 1: Подключитесь к серверу

```bash
ssh user@your-server-ip
```

### Шаг 2: Перейдите в директорию проекта

```bash
cd /path/to/Sales\ bot
```

### Шаг 3: Получите последние изменения

```bash
git pull origin main
```

### Шаг 4: Остановите бота

```bash
docker compose down
```

### Шаг 5: Пересоберите контейнеры

```bash
docker compose build --no-cache
```

### Шаг 6: Запустите бота

```bash
docker compose up -d
```

### Шаг 7: Проверьте логи

```bash
docker compose logs -f bot
```

Нажмите `Ctrl+C` для выхода из просмотра логов.

---

## Вариант с сохранением данных

Если в базе есть важные данные и вы хотите их сохранить:

```bash
# 1. Подключитесь к серверу
ssh user@your-server-ip

# 2. Перейдите в директорию проекта
cd /path/to/Sales\ bot

# 3. Получите изменения
git pull origin main

# 4. Пересоберите только контейнер бота (БД не трогаем)
docker compose build bot

# 5. Перезапустите только бота
docker compose restart bot

# 6. Проверьте логи
docker compose logs -f bot
```

---

## Вариант с полной очисткой (если нет важных данных)

```bash
# 1. Подключитесь к серверу
ssh user@your-server-ip

# 2. Перейдите в директорию проекта
cd /path/to/Sales\ bot

# 3. Получите изменения
git pull origin main

# 4. Остановите все контейнеры и удалите volumes
docker compose down -v

# 5. Пересоберите контейнеры
docker compose build --no-cache

# 6. Запустите все сервисы
docker compose up -d

# 7. Проверьте логи
docker compose logs -f bot
```

---

## Проверка успешного обновления

После запуска проверьте логи на наличие ошибок:

```bash
docker compose logs bot | grep -i error
```

Если ошибок нет, проверьте что бот работает:

```bash
docker compose ps
```

Все сервисы должны быть в статусе `Up`.

---

## Откат на предыдущую версию (если что-то пошло не так)

```bash
# 1. Остановите контейнеры
docker compose down

# 2. Откатите изменения в git
git reset --hard HEAD~1

# 3. Пересоберите и запустите
docker compose build --no-cache
docker compose up -d
```

---

## Полезные команды для мониторинга

### Просмотр логов в реальном времени
```bash
docker compose logs -f bot
```

### Просмотр последних 100 строк логов
```bash
docker compose logs --tail=100 bot
```

### Проверка статуса всех сервисов
```bash
docker compose ps
```

### Проверка использования ресурсов
```bash
docker stats
```

### Зайти внутрь контейнера бота
```bash
docker compose exec bot bash
```

### Проверить версию миграции БД
```bash
docker compose exec bot alembic current
```

### Применить миграции вручную
```bash
docker compose exec bot alembic upgrade head
```

---

## Автоматический скрипт обновления

Создайте файл `update.sh` на сервере:

```bash
#!/bin/bash

echo "🔄 Начинаю обновление бота..."

# Переход в директорию проекта
cd /path/to/Sales\ bot || exit 1

# Получение изменений
echo "📥 Получаю изменения из git..."
git pull origin main

# Остановка контейнеров
echo "⏸️ Останавливаю контейнеры..."
docker compose down

# Пересборка
echo "🔨 Пересобираю контейнеры..."
docker compose build --no-cache

# Запуск
echo "🚀 Запускаю бота..."
docker compose up -d

# Ожидание запуска
echo "⏳ Жду 10 секунд..."
sleep 10

# Проверка логов
echo "📋 Проверяю логи..."
docker compose logs --tail=50 bot

echo "✅ Обновление завершено!"
```

Сделайте скрипт исполняемым:

```bash
chmod +x update.sh
```

Используйте для обновления:

```bash
./update.sh
```

---

## Настройка автоматического обновления через cron

Для автоматического обновления каждую ночь в 3:00:

```bash
# Откройте crontab
crontab -e

# Добавьте строку
0 3 * * * cd /path/to/Sales\ bot && ./update.sh >> /var/log/bot-update.log 2>&1
```

---

## Решение типичных проблем

### Проблема: "Cannot connect to the Docker daemon"

```bash
sudo systemctl start docker
```

### Проблема: "Port is already in use"

```bash
# Найдите процесс, использующий порт
sudo lsof -i :5432  # для PostgreSQL
sudo lsof -i :6379  # для Redis

# Остановите старые контейнеры
docker compose down
```

### Проблема: "No space left on device"

```bash
# Очистите неиспользуемые Docker образы и контейнеры
docker system prune -a --volumes

# Проверьте свободное место
df -h
```

### Проблема: Миграция не применяется

```bash
# Зайдите в контейнер
docker compose exec bot bash

# Проверьте текущую версию
alembic current

# Примените миграцию вручную
alembic upgrade head

# Выйдите
exit
```

---

## Мониторинг и алерты

### Настройка healthcheck

Бот уже имеет встроенный healthcheck. Проверьте его работу:

```bash
docker compose exec bot python healthcheck.py
```

### Настройка уведомлений в Telegram

Добавьте в `.env` на сервере:

```env
ADMIN_TELEGRAM_ID=your_telegram_id
```

Бот будет отправлять критические ошибки администратору.

---

## Бэкап базы данных

### Создание бэкапа

```bash
# Создайте директорию для бэкапов
mkdir -p backups

# Создайте бэкап
docker compose exec postgres pg_dump -U finance_user finance_bot > backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
# Остановите бота
docker compose stop bot

# Восстановите базу
cat backups/backup_20250123_120000.sql | docker compose exec -T postgres psql -U finance_user finance_bot

# Запустите бота
docker compose start bot
```

---

## Контакты для поддержки

При возникновении проблем:

1. Проверьте логи: `docker compose logs bot`
2. Проверьте документацию в `docs/`
3. Создайте issue в репозитории проекта


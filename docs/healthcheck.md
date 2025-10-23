# 🏥 Docker Healthcheck

## Обзор

Контейнер бота включает автоматический healthcheck для мониторинга жизнеспособности приложения. Healthcheck выполняется каждые 30 секунд и проверяет реальную работоспособность бота.

## Что проверяется

### 1. Подключение к Telegram API (критично)
- Выполняется HTTP GET запрос к `https://api.telegram.org/bot<token>/getMe`
- Проверяется, что бот может подключиться к Telegram
- Проверяется, что токен валиден
- Timeout: 5 секунд

### 2. Свежесть лог-файла (предупреждение)
- Проверяется, что файл `/app/logs/bot.log` обновлялся в последние 5 минут
- Это дополнительная проверка активности процесса
- Не влияет на статус healthcheck (только warning)

## Параметры healthcheck

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3
```

- **interval**: 30 секунд между проверками
- **timeout**: 10 секунд на выполнение проверки
- **start-period**: 40 секунд grace period после старта контейнера
- **retries**: 3 неудачные попытки подряд = unhealthy

## Статусы

### `starting`
Контейнер только запустился, healthcheck еще не прошел первый раз. Это нормально в первые 40 секунд после старта.

### `healthy`
✅ Бот работает нормально:
- Подключение к Telegram API успешно
- Бот может получать и обрабатывать сообщения

### `unhealthy`
❌ Бот не работает:
- Не может подключиться к Telegram API
- Токен невалиден
- Сетевые проблемы
- Процесс завис

## Проверка статуса

### В Docker Compose

```bash
# Посмотреть статус всех контейнеров
docker compose ps

# Вывод:
# NAME    IMAGE    STATUS
# bot     ...      Up 2 minutes (healthy)
# db      ...      Up 2 minutes (healthy)
# redis   ...      Up 2 minutes (healthy)
```

### Через Docker

```bash
# Детальная информация о healthcheck
docker inspect --format='{{json .State.Health}}' sales-bot | jq

# Логи healthcheck
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' sales-bot
```

### Через Makefile

```bash
# Проверить здоровье всех сервисов
make health
```

## Локальное тестирование

Перед деплоем можно протестировать healthcheck локально:

```bash
# Активировать виртуальное окружение
source venv/Scripts/activate  # Windows Git Bash

# Запустить тест healthcheck
python check_healthcheck.py
```

**Ожидаемый вывод при успехе:**
```
Testing healthcheck script...
BOT_TOKEN present: Yes
--------------------------------------------------
OK: Bot is alive and connected to Telegram
--------------------------------------------------
✅ Healthcheck PASSED
```

**Ожидаемый вывод при ошибке:**
```
Testing healthcheck script...
BOT_TOKEN present: Yes
--------------------------------------------------
ERROR: HTTP 401
--------------------------------------------------
❌ Healthcheck FAILED
```

## Troubleshooting

### Healthcheck всегда unhealthy

**Причина 1: Невалидный токен**
```bash
# Проверить токен в .env
grep BOT_TOKEN .env

# Проверить токен вручную
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

**Причина 2: Сетевые проблемы**
```bash
# Проверить, что контейнер может достучаться до интернета
docker compose exec bot ping -c 3 api.telegram.org

# Проверить DNS
docker compose exec bot nslookup api.telegram.org
```

**Причина 3: Firewall блокирует запросы**
- Убедитесь, что исходящие HTTPS запросы (порт 443) разрешены
- Проверьте правила iptables/firewall на хосте

### Healthcheck starting слишком долго

Если контейнер остается в статусе `starting` более 40 секунд:

```bash
# Посмотреть логи бота
docker compose logs bot

# Проверить, запустился ли процесс Python
docker compose exec bot ps aux | grep python
```

### Warning о свежести логов

Это не критично, но может указывать на проблемы:

```bash
# Проверить, пишутся ли логи
docker compose exec bot tail -f /app/logs/bot.log

# Проверить права на директорию логов
docker compose exec bot ls -la /app/logs/
```

## Интеграция с мониторингом

### Docker Swarm

При использовании Docker Swarm healthcheck автоматически используется для:
- Определения готовности сервиса
- Автоматического перезапуска unhealthy контейнеров
- Load balancing (не направлять трафик на unhealthy инстансы)

### Kubernetes

Для Kubernetes можно использовать аналогичную логику в liveness/readiness probes:

```yaml
livenessProbe:
  exec:
    command:
    - python
    - /app/healthcheck.py
  initialDelaySeconds: 40
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  exec:
    command:
    - python
    - /app/healthcheck.py
  initialDelaySeconds: 10
  periodSeconds: 10
```

### Prometheus/Grafana

Можно экспортировать метрики healthcheck:

```bash
# Получить статус в формате для Prometheus
docker inspect --format='{{.State.Health.Status}}' sales-bot | \
  awk '{print "bot_health_status{status=\""$1"\"} 1"}'
```

## Кастомизация

### Изменить интервал проверки

Отредактируйте `Dockerfile`:

```dockerfile
HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py
```

### Добавить дополнительные проверки

Отредактируйте `healthcheck.py`:

```python
def check_database() -> bool:
    """Check database connectivity."""
    # Your implementation
    pass

def main() -> int:
    if not check_telegram_api():
        return 1
    
    if not check_database():
        return 1
    
    return 0
```

### Отключить healthcheck

В `docker-compose.yml`:

```yaml
services:
  bot:
    healthcheck:
      disable: true
```

## Безопасность

⚠️ **Важно**: Healthcheck использует `BOT_TOKEN` для проверки подключения к Telegram API.

- Токен передается через environment variable
- Токен НЕ логируется в stdout/stderr
- Используется HTTPS для всех запросов
- Timeout защищает от зависания

## См. также

- [Deployment Guide](deployment_guide.md) - полное руководство по деплою
- [Docker Documentation](https://docs.docker.com/engine/reference/builder/#healthcheck) - официальная документация HEALTHCHECK


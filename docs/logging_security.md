# Безопасность логирования

## Обзор

Система логирования настроена с автоматическим маскированием чувствительных данных для предотвращения утечек секретов (API ключей, токенов, паролей) в лог-файлы.

## Компоненты безопасности

### 1. Автоматическое маскирование в логах

**Файл:** `src/utils/logger.py`

Все сообщения, проходящие через систему логирования, автоматически проверяются и маскируются:

- **API ключи и токены** (строки 20+ символов) → `sk-1234************`
- **URL с credentials** → `postgresql://user:***@host:5432/db`
- **Пароли и секреты** в тексте сообщений

```python
# Пример использования
logger.info(f"Connecting to {database_url}")
# В логах: "Connecting to postgresql://user:***@localhost:5432/mydb"
```

### 2. Утилиты для маскирования

**Файл:** `src/utils/sanitizer.py`

Предоставляет функции для ручного маскирования чувствительных данных:

#### `mask_sensitive_value(value, visible_chars=4)`
Маскирует строку, оставляя видимыми только первые N символов.

```python
from src.utils.sanitizer import mask_sensitive_value

api_key = "sk-1234567890abcdef"
safe_key = mask_sensitive_value(api_key)
# Результат: "sk-1***************"
```

#### `sanitize_dict(data, sensitive_keys=None)`
Маскирует значения чувствительных ключей в словарях.

```python
from src.utils.sanitizer import sanitize_dict

config = {
    "api_key": "secret123",
    "username": "john",
    "password": "mypass"
}
safe_config = sanitize_dict(config)
# Результат: {"api_key": "secr*****", "username": "john", "password": "mypa**"}
```

#### `sanitize_url(url)`
Маскирует credentials в URL.

```python
from src.utils.sanitizer import sanitize_url

db_url = "postgresql://admin:secret123@localhost:5432/mydb"
safe_url = sanitize_url(db_url)
# Результат: "postgresql://admin:***@localhost:5432/mydb"
```

#### `sanitize_headers(headers)`
Маскирует токены в HTTP заголовках.

```python
from src.utils.sanitizer import sanitize_headers

headers = {
    "Authorization": "Bearer sk-123456",
    "Content-Type": "application/json"
}
safe_headers = sanitize_headers(headers)
# Результат: {"Authorization": "Bear**********", "Content-Type": "application/json"}
```

#### `sanitize_exception_message(exception)`
Маскирует чувствительные данные в сообщениях исключений.

```python
from src.utils.sanitizer import sanitize_exception_message

try:
    raise ValueError("Invalid token: sk-1234567890abcdef")
except ValueError as e:
    safe_error = sanitize_exception_message(e)
    logger.error(f"Error: {safe_error}")
    # В логах: "Error: Invalid token: sk-1***************"
```

## Применение в коде

### 1. Логирование ошибок конфигурации

**Файл:** `main.py`

```python
try:
    config_settings = get_settings()
except Exception as e:
    from src.utils.sanitizer import sanitize_exception_message
    safe_error = sanitize_exception_message(e)
    logger.critical(f"❌ Ошибка загрузки конфигурации: {safe_error}")
```

### 2. Логирование HTTP ответов

**Файл:** `src/services/openrouter_service.py`

```python
if response.status_code != 200:
    # Truncate and sanitize response
    safe_response = response.text[:200]
    logger.error(f"API error {response.status_code}: {safe_response}")
```

### 3. Логирование исключений в middleware

**Файл:** `src/middlewares/error_handler.py`

```python
except TelegramAPIError as e:
    from src.utils.sanitizer import sanitize_exception_message
    safe_error = sanitize_exception_message(e)
    logger.error(f"❌ Telegram API Error: {safe_error}")
```

### 4. Логирование исключений в handlers

**Файл:** `src/handlers/voice.py`, `src/handlers/transactions.py`, etc.

```python
except Exception as e:
    from src.utils.sanitizer import sanitize_exception_message
    safe_error = sanitize_exception_message(e)
    logger.error(f"Ошибка обработки: {safe_error}")
```

## Список защищенных паттернов

### Автоматически маскируемые ключевые слова:
- `token`, `api_key`, `apikey`, `api-key`
- `password`, `passwd`, `pwd`
- `secret`, `authorization`, `auth`
- `bot_token`, `agentrouter_api_key`
- `database_url`, `redis_url`
- `access_token`, `refresh_token`
- `private_key`, `secret_key`

### Автоматически маскируемые паттерны:
- Строки 20+ символов (потенциальные токены)
- URL с embedded credentials (`scheme://user:pass@host`)
- HTTP заголовки Authorization, X-API-Key

## Best Practices

### ✅ DO:
1. **Всегда используйте `sanitize_exception_message`** при логировании исключений
2. **Маскируйте URL** перед логированием подключений к БД/Redis
3. **Ограничивайте длину** логируемых HTTP ответов (макс. 200 символов)
4. **Проверяйте логи** на наличие чувствительных данных после изменений

### ❌ DON'T:
1. **Не логируйте** полные объекты конфигурации
2. **Не логируйте** полные HTTP запросы/ответы с headers
3. **Не логируйте** сырые данные от пользователей без валидации
4. **Не используйте** `logger.debug()` для вывода токенов даже в dev-режиме

## Проверка безопасности логов

### Ручная проверка
```bash
# Поиск потенциальных токенов в логах (строки 20+ символов)
grep -E '[a-zA-Z0-9_-]{20,}' logs/bot.log

# Поиск паттернов паролей
grep -i 'password.*:' logs/bot.log

# Поиск API ключей
grep -i 'api.key' logs/bot.log
```

### Автоматическая проверка
Система логирования автоматически маскирует все подозрительные паттерны перед записью в файл.

## Примеры использования

### Пример 1: Логирование подключения к Redis
```python
from src.utils.sanitizer import sanitize_url

redis_url = config_settings.redis_url
safe_redis_url = sanitize_url(redis_url)
logger.info(f"✅ Connected to Redis: {safe_redis_url}")
```

### Пример 2: Логирование ошибки API
```python
from src.utils.sanitizer import sanitize_exception_message

try:
    response = await api_client.post(url, headers=headers)
except Exception as e:
    safe_error = sanitize_exception_message(e)
    logger.error(f"API request failed: {safe_error}")
```

### Пример 3: Логирование конфигурации
```python
from src.utils.sanitizer import sanitize_dict

config = {
    "bot_token": settings.bot_token,
    "database_url": settings.database_url,
    "log_level": settings.log_level
}
safe_config = sanitize_dict(config)
logger.debug(f"Configuration loaded: {safe_config}")
```

## Тестирование

### Проверка маскирования
```python
from src.utils.sanitizer import mask_sensitive_value, sanitize_url

# Test 1: Mask API key
assert mask_sensitive_value("sk-1234567890") == "sk-1*******"

# Test 2: Sanitize URL
url = "postgresql://user:pass@localhost/db"
assert sanitize_url(url) == "postgresql://user:***@localhost/db"
```

## Обновление правил маскирования

Для добавления новых паттернов маскирования:

1. Откройте `src/utils/sanitizer.py`
2. Добавьте ключевое слово в `sensitive_keys` (функция `sanitize_dict`)
3. Или добавьте regex паттерн в функции маскирования

Пример:
```python
sensitive_keys = {
    "token", "api_key", "password",
    "your_new_sensitive_key"  # Добавьте здесь
}
```

## Мониторинг

### Регулярные проверки:
- Еженедельный аудит лог-файлов на утечки
- Автоматические алерты при обнаружении паттернов токенов
- Review изменений в коде, связанных с логированием

### Инциденты:
При обнаружении утечки чувствительных данных в логах:
1. Немедленно ротировать скомпрометированные ключи
2. Удалить лог-файлы с утечкой
3. Обновить правила маскирования
4. Провести аудит остальных логов

## Заключение

Система автоматического маскирования защищает от случайных утечек секретов в логи. Однако важно следовать best practices и регулярно проверять логи на наличие чувствительных данных.

**Помните:** Лучшая защита - не логировать чувствительные данные вообще. Используйте маскирование только как дополнительный уровень защиты.


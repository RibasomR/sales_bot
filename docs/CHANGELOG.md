# 📝 Changelog

Все значимые изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект следует [Semantic Versioning](https://semver.org/lang/ru/).

---

## [1.2.7] - 2025-10-24

### 🐛 Исправления

#### Исправлена ошибка миграции на production
- **FIX**: Улучшена проверка существования ENUM типов в миграции
- **Проблема**: При запуске на сервере возникала ошибка `DuplicateObjectError: type "category_type" already exists`
- **Решение**: Исправлен метод получения результата проверки существования типа (`.scalar()` → `.fetchone()[0]`)
- **Файл**: `alembic/versions/2025_01_19_1200-001_initial_migration.py`

### 📚 Документация

#### Добавлены руководства по устранению проблем
- **Новый файл**: `docs/IMMEDIATE_FIX.md` - срочные команды Docker для немедленного решения
- **Новый файл**: `docs/migration_fix.md` - подробное руководство по исправлению ошибок миграции
- **Новый файл**: `docs/QUICK_FIX.md` - краткая инструкция для быстрого решения (Docker + Docker Compose)
- **Новый файл**: `docs/VOLUME_NAMES.md` - определение и удаление Docker volumes
- **Новый файл**: `docs/SERVER_QUICKSTART.md` - быстрый старт на сервере за 5 минут
- **Новый скрипт**: `diagnose.sh` - автоматическая диагностика проблем деплоя
- **Обновлен**: `docs/deployment_guide.md` - добавлен раздел troubleshooting для ошибок миграции
- **Обновлен**: `docs/README.md` - добавлена секция "Решение проблем"
- **Обновлен**: `Makefile` - добавлена команда `make diagnose`

#### Содержание новых руководств
- ✅ 3 варианта решения проблемы с ENUM типами
- ✅ Инструкции по созданию бэкапов базы данных
- ✅ Команды для диагностики состояния БД
- ✅ Шаги по обновлению кода на сервере через Git/SCP
- ✅ Проверка работоспособности после исправления
- ✅ Автоматический скрипт диагностики с проверкой 9 параметров

### 🔧 Улучшения

#### Обновлена поддержка Docker Compose v2
- **Обновлены все скрипты**: замена `docker-compose` на `docker compose`
- **Файлы**: `diagnose.sh`, `Makefile`, `docs/QUICK_FIX.md`, `docs/migration_fix.md`, `docs/deployment_guide.md`, `docs/SERVER_QUICKSTART.md`
- **Совместимость**: `deploy.sh` поддерживает обе версии (v1 и v2)
- **Исправлены имена**: обновлены имена контейнеров и пользователей БД в документации

---

## [1.2.6] - 2025-10-24

### 🔒 Безопасность

#### Автоматическое маскирование чувствительных данных в логах
- **SECURITY**: Добавлена система автоматического маскирования секретов в логах
- **Новый модуль**: `src/utils/sanitizer.py` - утилиты для маскирования чувствительных данных
- **Обновлен**: `src/utils/logger.py` - автоматическое маскирование в системе логирования

#### Защищенные паттерны
- ✅ API ключи и токены (строки 20+ символов) → `sk-1234************`
- ✅ URL с credentials → `postgresql://user:***@host:5432/db`
- ✅ Пароли и секреты в exception messages
- ✅ HTTP заголовки (Authorization, X-API-Key)
- ✅ Database URLs в логах подключений

#### Обновленные файлы
- `src/utils/sanitizer.py` - новый модуль с функциями маскирования
- `src/utils/logger.py` - добавлен автоматический filter для маскирования
- `main.py` - маскирование в логах инициализации
- `src/services/openrouter_service.py` - маскирование API ключей и ошибок
- `src/middlewares/error_handler.py` - маскирование в exception handlers
- `src/handlers/voice.py` - маскирование в логах обработки голоса
- `src/handlers/transactions.py` - маскирование в логах транзакций
- `src/handlers/export.py` - маскирование в логах экспорта
- `src/handlers/categories.py` - маскирование в логах категорий

#### Новая документация
- `docs/logging_security.md` - полное руководство по безопасности логирования

#### Функции маскирования
```python
from src.utils.sanitizer import (
    mask_sensitive_value,      # Маскирование строк
    sanitize_dict,              # Маскирование словарей
    sanitize_url,               # Маскирование URL
    sanitize_headers,           # Маскирование HTTP headers
    sanitize_exception_message, # Маскирование exceptions
    sanitize_for_logging        # Общее маскирование текста
)
```

#### Преимущества
- 🔒 Защита от утечки API ключей в лог-файлы
- 🔒 Защита от утечки паролей БД в логах ошибок
- 🔒 Защита токенов в HTTP запросах/ответах
- 🔒 Автоматическое маскирование без изменения кода
- 🔒 Дополнительные утилиты для ручного маскирования

---

## [1.2.5] - 2025-10-24

### 🔧 Улучшения

#### Consolidation of Alembic Migrations
- **REFACTOR**: Объединены все миграции в одну начальную миграцию `001_initial_migration`
- **Удалены** устаревшие миграции:
  - `7fec9f3b445e_add_user_settings_fields` - поле `monthly_limit` теперь в начальной миграции
  - `0f8ce514bbc2_add_composite_indexes_for_optimization` - композитные индексы теперь в начальной миграции
  - `45daad71f78d_convert_timestamps_to_timezone_aware` - timezone-aware timestamps теперь в начальной миграции
- **Преимущества**:
  - Упрощенная история миграций
  - Быстрее развертывание с нуля
  - Меньше потенциальных проблем с зависимостями
  - Единая точка входа для схемы БД

#### Обновленная начальная миграция включает
- ✅ Все таблицы: `users`, `categories`, `transactions`
- ✅ ENUM типы для PostgreSQL: `category_type`, `transaction_type`
- ✅ Timezone-aware timestamps (TIMESTAMPTZ) для PostgreSQL
- ✅ Все поля включая `monthly_limit` и `max_transaction_limit`
- ✅ Все индексы (одиночные и композитные):
  - `ix_categories_user_type` - для фильтрации категорий
  - `ix_transactions_user_type` - для фильтрации транзакций по типу
  - `ix_transactions_user_created` - для фильтрации по дате
  - `ix_transactions_category_created` - для статистики по категориям
- ✅ Идемпотентное создание ENUM типов (не падает при повторном запуске)
- ✅ Поддержка как PostgreSQL, так и SQLite

#### Новые файлы
- `docs/migrations_guide.md` - полное руководство по работе с миграциями Alembic

#### Обновленные файлы
- `alembic/versions/2025_01_19_1200-001_initial_migration.py` - полностью переписана
- `alembic.ini` - обновлен комментарий о динамической установке URL
- `docs/CHANGELOG.md` - добавлена эта запись

#### Применение изменений
```bash
# Для новых развертываний - просто запустите
alembic upgrade head

# Для существующих БД - миграция не требуется (схема не изменилась)
# Но если хотите обновить историю миграций:
alembic downgrade base  # Откатить все
alembic upgrade head    # Применить новую единую миграцию
```

---

## [1.2.4] - 2025-10-24

### 🔧 Улучшения

#### Docker Healthcheck
- **IMPROVED**: Healthcheck теперь проверяет реальную жизнеспособность бота
- **Проверка Telegram API**: Каждые 30 секунд проверяется подключение через метод `getMe`
- **Проверка логов**: Дополнительная проверка свежести лог-файла
- **Новые файлы**:
  - `healthcheck.py` - скрипт для проверки здоровья бота
  - `check_healthcheck.py` - локальный тест healthcheck без Docker

#### Обновленные файлы
- `Dockerfile` - обновлен healthcheck с проверкой Telegram API вместо простого `exit(0)`
- `docs/deployment_guide.md` - добавлена документация по healthcheck

---

## [1.2.3] - 2025-10-24

### 🚀 Новые возможности

#### Redis-backed Rate Limiting
- **NEW**: Реализован масштабируемый rate limiter с поддержкой Redis
- **Архитектура**: Pluggable backend (Redis + in-memory fallback)
- **Автоматический fallback**: Бот автоматически переключается на in-memory хранилище если Redis недоступен
- **Production-ready**: Redis backend использует атомарные операции (INCR + EXPIRE) для точного контроля частоты запросов
- **Масштабируемость**: Поддержка нескольких инстансов бота с общим rate limiting через Redis

#### Новые файлы
- `check_redis.py` - тестовый скрипт для проверки Redis подключения и rate limiter
- `docs/redis_setup.md` - полная документация по настройке и использованию Redis

#### Обновленные файлы
- `src/utils/validators.py` - новая архитектура rate limiter с backend интерфейсом
  - `RateLimiterBackend` - абстрактный базовый класс
  - `InMemoryRateLimiterBackend` - fallback для dev/тестирования
  - `RedisRateLimiterBackend` - production backend с Redis
- `src/middlewares/rate_limit.py` - обновлен для использования async rate limiter
- `main.py` - логика инициализации Redis и выбора backend
- `config/config.py` - добавлен `redis_url` в настройки
- `env.example` - добавлены переменные `REDIS_URL` и `REDIS_PASSWORD`
- `docker-compose.yml` - Redis уже был настроен
- `docs/deployment_guide.md` - добавлены секции про Redis мониторинг и troubleshooting
- `docs/README.md` - добавлена ссылка на redis_setup.md

#### Логирование
- При запуске бота логируется активный backend:
  - `✅ Rate limiting активирован (Redis backend)` - Redis доступен
  - `✅ Rate limiting активирован (in-memory backend)` - fallback режим

#### Тестирование
```bash
# Проверка Redis и rate limiter
python check_redis.py

# Тесты включают:
# - Redis подключение (PING, SET, GET, INCR, EXPIRE, TTL)
# - In-memory backend (лимиты, блокировка, сброс)
# - Redis backend (лимиты, блокировка, сброс)
```

---

## [1.2.2] - 2025-10-24

### 🔧 Оптимизация архитектуры

#### Упрощение Docker-архитектуры
- **REFACTOR**: Убран отдельный whisper-сервис, whisper.cpp теперь встроен в основной контейнер бота
- **Удалено**: `Dockerfile.whisper`, `whisper_server.py`, `requirements.whisper.txt`
- **Упрощено**: Docker Compose теперь содержит только 3 сервиса (postgres, redis, bot) вместо 4
- **Преимущества**: Меньше сложности, меньше накладных расходов на сетевое взаимодействие, проще деплой

#### Обновленные файлы
- `docker-compose.yml` - убран whisper-сервис, добавлен volume для whisper_cache в основной контейнер
- `Dockerfile` - сохранена сборка whisper.cpp в основном образе
- `docs/deployment_guide.md` - обновлена секция проверки Whisper.cpp

---

## [1.2.1] - 2025-10-24

### 🔧 Исправления

#### Timezone-aware timestamps
- **FIX**: Все временные метки `created_at/updated_at` теперь используют `TIMESTAMP WITH TIME ZONE` (timestamptz) вместо `TIMESTAMP WITHOUT TIME ZONE`
- **Причина**: Предотвращение проблем со сравнением дат и агрегацией данных при работе с разными часовыми поясами
- **Миграция**: Создана Alembic миграция `45daad71f78d_convert_timestamps_to_timezone_aware`
- **Код**: Все вызовы `datetime.now()` заменены на `datetime.now(timezone.utc)` для консистентности

#### Обновленные файлы
- `src/models/base.py` - `TimestampMixin` теперь использует `DateTime(timezone=True)`
- `src/handlers/view.py` - использование timezone-aware datetime
- `src/handlers/export.py` - использование timezone-aware datetime
- `src/handlers/transactions.py` - использование timezone-aware datetime
- `src/handlers/settings.py` - использование timezone-aware datetime
- `alembic/versions/2025_10_24_0506-45daad71f78d_convert_timestamps_to_timezone_aware.py` - новая миграция

#### Применение миграции
```bash
# Локально
alembic upgrade head

# В Docker
docker compose exec bot alembic upgrade head
```

---

## [1.2.0] - 2025-10-23

### 🚀 Улучшение производительности

#### Миграция на Whisper.cpp
- **PERFORMANCE**: Заменен `openai-whisper` на `pywhispercpp` (whisper.cpp)
- **Ускорение**: Транскрибация теперь работает в **2-4 раза быстрее**
- **Память**: Снижено потребление RAM с ~2GB до ~500MB (-75%)
- **Docker**: Размер образа уменьшен с ~4GB до ~1GB (-75%)
- **Точность**: Сохранена на том же уровне (100%)

#### Изменения в зависимостях
- Удалены: `openai-whisper`, `torch`, `torchaudio`
- Добавлено: `pywhispercpp==1.2.0`

#### Изменения в конфигурации
- **Удалена**: переменная `WHISPER_DEVICE` (cpu/cuda)
- **Добавлена**: `WHISPER_THREADS` - количество CPU потоков (по умолчанию: 4)

#### Обновленные файлы
- `requirements.txt` - обновлены зависимости
- `requirements.whisper.txt` - обновлены зависимости для Whisper сервера
- `src/services/openrouter_service.py` - использование whisper.cpp API
- `whisper_server.py` - FastAPI сервер на whisper.cpp
- `Dockerfile.whisper` - оптимизированный образ без PyTorch
- `docker-compose.yml` - обновлена конфигурация whisper сервиса
- `env.example` - добавлены новые переменные окружения

#### Документация
- Создано руководство по миграции: `docs/MIGRATION_TO_WHISPER_CPP.md`
- Инструкции по обновлению для существующих развертываний
- Сравнительная таблица производительности

### 📚 Примечания к миграции

Для существующих пользователей:
1. Обновите `.env`: замените `WHISPER_DEVICE=cpu` на `WHISPER_THREADS=4`
2. Пересоберите Docker контейнеры: `docker compose build --no-cache`
3. Перезапустите: `docker compose up -d`
4. См. [MIGRATION_TO_WHISPER_CPP.md](MIGRATION_TO_WHISPER_CPP.md) для деталей

---

## [1.1.0] - 2025-10-22

### 🔄 Изменено

#### Миграция на AgentRouter
- **BREAKING**: Заменен OpenRouter на AgentRouter для парсинга транзакций
- Обновлена модель: DeepSeek V3.1 → DeepSeek V3.2
- Изменена переменная окружения: `OPENROUTER_API_KEY` → `AGENTROUTER_API_KEY`
- Обновлен базовый URL API: `https://openrouter.ai/api/v1` → `https://agentrouter.org/v1`
- Переименован файл: `check_openrouter.py` → `check_agentrouter.py`

#### Документация
- Создана документация по настройке AgentRouter (`docs/agentrouter_setup.md`)
- Создано руководство по миграции (`docs/MIGRATION_TO_AGENTROUTER.md`)
- Обновлены все ссылки на OpenRouter в документации
- Обновлен `env.example` с новыми переменными окружения

#### Код
- Обновлен `src/services/openrouter_service.py` для работы с AgentRouter API
- Обновлен `config/config.py` - изменено поле `agentrouter_api_key`
- Все комментарии в коде переведены на английский
- Улучшена обработка ошибок API

### 📚 Примечания к миграции

Для существующих пользователей:
1. Получите API ключ на [agentrouter.org/console/token](https://agentrouter.org/console/token)
2. Замените `OPENROUTER_API_KEY` на `AGENTROUTER_API_KEY` в `.env`
3. Перезапустите бота
4. См. [MIGRATION_TO_AGENTROUTER.md](MIGRATION_TO_AGENTROUTER.md) для деталей

---

## [1.0.0] - 2025-10-20

### 🚀 Добавлено

#### Docker деплой (Этап 11)
- Создан `Dockerfile` для основного приложения с мультистадийной сборкой
- Создан `Dockerfile.whisper` для локального Whisper API сервера
- Настроен `docker-compose.yml` с 4 сервисами (bot, postgres, redis, whisper)
- Добавлен `docker-compose.prod.yml` для production деплоя с ограничением ресурсов
- Создан `.dockerignore` для оптимизации сборки образов
- Добавлен `Makefile` с командами для управления Docker окружением
- Создан скрипт `deploy.sh` для автоматического деплоя
- Написан `whisper_server.py` - FastAPI сервер для локальной транскрибации
- Добавлен `.env.template.docker` с шаблоном переменных окружения
- Создан `requirements.whisper.txt` с зависимостями для Whisper сервера

#### Документация
- Создано подробное руководство по Docker деплою (`README.Docker.md`)
- Добавлено руководство по деплою на сервер (`docs/deployment_guide.md`)
- Написана документация по архитектуре Docker (`docs/docker_architecture.md`)
- Обновлен `roadmap.md` - отмечен завершенным Этап 11

#### Функционал
- Локальный Whisper API для транскрибации голосовых сообщений
- Health checks для всех сервисов
- Автоматическое применение миграций при запуске
- Система автоматических бэкапов (настраивается через cron)
- Ротация логов через Docker logging driver

### 🔧 Изменено

- Оптимизирована структура проекта для Docker
- Улучшена изоляция сервисов через Docker networks
- Настроено персистентное хранилище данных через Docker volumes

### 🛡️ Безопасность

- Изоляция сервисов в отдельной Docker сети
- Порты не экспонируются наружу в production режиме
- Все секреты вынесены в переменные окружения
- Ограничение ресурсов для контейнеров в production

### 📦 Инфраструктура

- PostgreSQL 15 Alpine для базы данных
- Redis 7 Alpine для кеширования
- Python 3.11 Slim для приложений
- Whisper API с поддержкой моделей tiny/base/small/medium/large

---

## [0.9.0] - 2025-01-20

### 🚀 Добавлено

#### Настройки пользователя (Этап 9)
- Меню настроек с возможностью установки лимитов
- Настройка максимальной суммы транзакции
- Установка месячного лимита трат
- Сохранение настроек в БД

#### Оптимизация и полировка (Этап 10)
- Добавлены составные индексы для оптимизации запросов
- Оптимизированы SQL запросы с использованием JOIN
- Проверка безопасности от SQL-инъекций
- Финальное тестирование всех функций
- Проверка корректности FSM состояний

#### Rate Limiting
- Настроена интеграция с Redis
- Реализован rate limiting для API запросов
- Реализован rate limiting для пользовательских действий
- Информативные сообщения при превышении лимита

#### Обработка ошибок
- Централизованный middleware для обработки ошибок
- Логирование всех критических ошибок
- Пользовательские сообщения об ошибках
- Fallback механизмы для БД и API

### 🔧 Изменено

- Миграция БД для добавления полей настроек пользователя
- Миграция БД для добавления составных индексов

---

## [0.8.0] - 2025-01-19

### 🚀 Добавлено

#### Экспорт данных (Этап 8)
- Функционал экспорта транзакций в Excel (XLSX)
- Команда `/export` для выгрузки данных
- Выбор периода для экспорта (сегодня, неделя, месяц, год, все время)
- Форматирование Excel файла с заголовками и стилями

---

## [0.7.0] - 2025-01-18

### 🚀 Добавлено

#### Управление категориями (Этап 7)
- Раздел настроек категорий
- Просмотр категорий расходов и доходов
- Добавление пользовательских категорий
- Редактирование названия и эмодзи категории
- Удаление пользовательских категорий с проверкой транзакций
- Защита предустановленных категорий от редактирования/удаления

---

## [0.6.0] - 2025-01-17

### 🚀 Добавлено

#### Просмотр транзакций (Этап 6)
- Главное меню с inline-кнопками
- Просмотр всех транзакций с пагинацией
- Фильтрация по типу (доходы/расходы)
- Фильтрация по периоду (сегодня, вчера, неделя, месяц, год)
- Удаление транзакций с подтверждением
- Редактирование существующих транзакций
- Статистика с балансом и топ-3 категориями

---

## [0.5.0] - 2025-01-16

### 🚀 Добавлено

#### Голосовой ввод (Этап 5)
- Интеграция с AgentRouter API для обработки голоса
- Транскрибация аудио через Whisper API
- Парсинг текста через DeepSeek v3.1:free
- Обработка голосовых сообщений
- Подтверждение/отмена/редактирование распознанных данных
- Retry механизм для API запросов
- Обработка ошибок транскрибации и парсинга

---

## [0.4.0] - 2025-01-15

### 🚀 Добавлено

#### Ручной ввод транзакций (Этап 4)
- FSM для пошагового ввода транзакций
- Команда `/add` с выбором типа операции
- Ввод суммы с валидацией
- Выбор категории из предустановленных
- Добавление пользовательских категорий
- Ввод описания (опционально)
- Подтверждение перед сохранением
  - Быстрый ввод через команду с параметрами

---

## [0.3.0] - 2025-01-14

### 🚀 Добавлено

#### База данных и модели (Этап 3)
- Подключение к PostgreSQL через SQLAlchemy (async)
- Модель `User` для пользователей
- Модель `Category` для категорий транзакций
- Модель `Transaction` для финансовых операций
- Настройка Alembic для миграций
- Первая миграция с созданием таблиц
- Сервисный слой для работы с БД
- Предустановленные категории доходов и расходов

---

## [0.2.0] - 2025-01-13

### 🚀 Добавлено

#### Базовая инфраструктура (Этап 2)
- Конфигурационный модуль для переменных окружения
- Система логирования через loguru
- Базовая структура aiogram бота
- Команда `/start` с приветствием
- Команда `/help` со справкой
- Middleware для обработки ошибок

---

## [0.1.0] - 2025-01-12

### 🚀 Добавлено

#### Инициализация проекта (Этап 1)
- Структура проекта (src, docs, config)
- Виртуальное окружение Python 3.11
- `requirements.txt` с зависимостями
- `.env.example` с шаблоном переменных
- `.gitignore` для Python/Git
- Git репозиторий
- `README.md` с описанием проекта

---

## Легенда типов изменений

- 🚀 **Добавлено** - новый функционал
- 🔧 **Изменено** - изменения в существующем функционале
- 🐛 **Исправлено** - исправление багов
- 🗑️ **Удалено** - удаленный функционал
- 🛡️ **Безопасность** - изменения связанные с безопасностью
- 📦 **Зависимости** - обновление зависимостей

---

[1.0.0]: https://github.com/your-repo/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/your-repo/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/your-repo/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/your-repo/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/your-repo/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/your-repo/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/your-repo/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/your-repo/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/your-repo/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-repo/releases/tag/v0.1.0

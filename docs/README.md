# 💰 Finance Telegram Bot - Документация

Telegram-бот для учета личных доходов и расходов с голосовым вводом транзакций.

## 📚 Содержание

- [Настройка базы данных](database_setup.md) - PostgreSQL/SQLite
- [Миграции базы данных](migrations_guide.md) - работа с Alembic миграциями
- [Настройка Redis](redis_setup.md) - для масштабируемого rate limiting
- [Настройка AgentRouter](agentrouter_setup.md) - для точного парсинга голоса
- [Руководство по деплою](deployment_guide.md) - продакшен на сервере
- [План развития](roadmap.md) - что уже сделано и что планируется
- [История изменений](CHANGELOG.md) - все обновления проекта

## ✨ Основные возможности

### 🎤 Голосовой ввод
Отправь голосовое сообщение боту:
> "Потратил 500 рублей на продукты"

Бот автоматически:
- Распознает речь через локальный **Whisper.cpp** (⚡ в 2-4 раза быстрее openai-whisper)
- Парсит транзакцию через AgentRouter API (DeepSeek V3.2)
- Извлечёт сумму, категорию и тип транзакции
- Покажет для подтверждения
- Сохранит в базу данных

⚠️ **Требует настройки AgentRouter API** - см. [инструкцию](agentrouter_setup.md)

### 📝 Ручной ввод
- `/add` - пошаговый ввод транзакции
- `/add расход 300 кафе` - быстрый ввод

### 📊 Просмотр и статистика
- `/transactions` - все транзакции
- `/stats` - баланс, доходы, расходы, топ категорий
- Фильтрация по периодам (день, неделя, месяц, год)

### 🏷️ Категории
- Предустановленные категории (Продукты, Транспорт, Зарплата и др.)
- Создание своих категорий
- Редактирование и удаление

### 📤 Экспорт
- `/export` - выгрузка данных в Excel (XLSX)
- Выбор периода экспорта
- Отправка файла в чат

### ⚙️ Настройки
- Лимиты транзакций
- Месячные лимиты трат
- Персональные настройки

## 🚀 Быстрый старт

```bash
# 1. Клонируй репозиторий
git clone <repo-url>
cd finance-bot

# 2. Создай виртуальное окружение
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# или: venv\Scripts\activate  # Windows CMD

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Создай .env файл
cp .env.example .env
# Добавь BOT_TOKEN от @BotFather

# 5. Примени миграции
alembic upgrade head

# 6. Запусти бота
python main.py
```

## 🔧 Технологии

- **Python 3.11+**
- **aiogram 3.x** - асинхронная библиотека для Telegram Bot API
- **SQLAlchemy** - ORM для работы с БД
- **PostgreSQL / SQLite** - база данных
- **Redis** - распределенный rate limiting (опционально, с автоматическим fallback)
- **Whisper.cpp** - локальная транскрипция голоса (⚡ 2-4x быстрее openai-whisper)
- **AgentRouter API** - парсинг транзакций через DeepSeek V3.2
- **Alembic** - миграции БД
- **Loguru** - логирование
- **Pydantic** - валидация данных

## 📖 Архитектура

```
src/
├── handlers/         # Обработчики команд и сообщений
├── keyboards/        # Inline клавиатуры
├── models/           # SQLAlchemy модели
├── services/         # Бизнес-логика (БД, AgentRouter, экспорт)
├── states/           # FSM состояния
├── middlewares/      # Middlewares (rate limit, errors)
└── utils/            # Утилиты (логирование, валидация)

config/               # Конфигурация
docs/                 # Документация
alembic/              # Миграции БД
```

## 🔒 Безопасность

- ✅ Все секреты в `.env` (не коммитятся)
- ✅ Валидация всех пользовательских данных
- ✅ Защита от SQL-инъекций через ORM
- ✅ Rate limiting для защиты от спама
- ✅ Обработка ошибок без раскрытия деталей пользователю

## 📝 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота и приветствие |
| `/menu` | Главное меню |
| `/add` | Добавить транзакцию |
| `/transactions` | Просмотр всех транзакций |
| `/stats` | Статистика |
| `/categories` | Управление категориями |
| `/export` | Экспорт данных |
| `/settings` | Настройки |
| `/help` | Справка |

Плюс:
- 🎤 Отправь голосовое сообщение для быстрого добавления

## 🎯 Roadmap

См. [roadmap.md](roadmap.md) для полного плана развития.

### ✅ Готово (v1.2)
- Голосовой ввод (Whisper + AgentRouter)
- Ручной ввод транзакций
- Просмотр и статистика
- Управление категориями
- Экспорт в Excel
- Настройки пользователя
- Docker деплой с healthcheck
- Redis-backed rate limiting

### 🔜 Планируется (v1.3)
- Повторяющиеся транзакции
- Бюджеты по категориям
- Графики и диаграммы
- Telegram Web App интеграция

## 🤝 Участие в разработке

1. Fork репозитория
2. Создай ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Открой Pull Request

## 📄 Лицензия

MIT License - см. [LICENSE](../LICENSE)

## 💬 Поддержка

Если возникли вопросы или проблемы:
1. Проверь [quickstart.md](quickstart.md)
2. Посмотри логи: `tail -f logs/bot.log`
3. Открой Issue на GitHub

## 🙏 Благодарности

- [aiogram](https://github.com/aiogram/aiogram) - отличная библиотека для Telegram Bot API
- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) - высокопроизводительная реализация Whisper на C/C++
- [pywhispercpp](https://github.com/abdeladim-s/pywhispercpp) - Python-биндинги для whisper.cpp
- [OpenAI Whisper](https://github.com/openai/whisper) - оригинальная модель для распознавания речи
- [AgentRouter](https://agentrouter.org) - единый API-шлюз для доступа к LLM моделям
- [DeepSeek](https://deepseek.com) - мощная LLM модель

---

**Приятного использования! 💰**

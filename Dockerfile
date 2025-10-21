## Dockerfile для Telegram-бота учета финансов
## Мультистадийная сборка для оптимизации размера образа

FROM python:3.11-slim as builder

WORKDIR /app

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

## Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для runtime
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копирование установленных пакетов из builder
COPY --from=builder /root/.local /root/.local

# Добавление PATH для пользовательских пакетов
ENV PATH=/root/.local/bin:$PATH

# Копирование кода приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.exit(0)"

# Запуск бота
CMD ["python", "main.py"]



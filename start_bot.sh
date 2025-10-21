#!/bin/bash
# Скрипт для запуска бота

echo "🚀 Запуск Telegram бота..."

# Активируем виртуальное окружение
if [ -d "venv" ]; then
    source venv/Scripts/activate
    echo "✅ Виртуальное окружение активировано"
else
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его командой: python -m venv venv"
    exit 1
fi

# Проверяем наличие .env
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте его на основе .env.example"
    exit 1
fi

# Очищаем кэш Python
echo "🧹 Очистка кэша..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Запускаем бота
echo "▶️  Запуск бота..."
python main.py


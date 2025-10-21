#!/bin/bash
# Скрипт для остановки всех экземпляров бота

echo "🛑 Остановка всех экземпляров бота..."

# Для Windows Git Bash
if command -v taskkill &> /dev/null; then
    echo "Используем taskkill (Windows)..."
    taskkill //F //IM python.exe 2>/dev/null || echo "Нет запущенных процессов Python"
else
    # Для Linux/Mac
    echo "Используем pkill (Linux/Mac)..."
    pkill -9 -f "python.*main.py" 2>/dev/null || echo "Нет запущенных процессов бота"
fi

echo "✅ Все процессы остановлены"
sleep 2


#!/bin/bash
## Quick deploy and health check script

set -e

echo "🚀 Начинаю деплой бота..."

# Stop existing containers
echo "⏹️ Остановка существующих контейнеров..."
docker-compose down || true

# Build and start
echo "🔨 Сборка и запуск контейнеров..."
docker-compose up -d --build

# Wait for services
echo "⏳ Ожидание запуска сервисов (60 секунд)..."
sleep 60

# Check container status
echo ""
echo "📊 Статус контейнеров:"
docker-compose ps

# Check bot logs
echo ""
echo "📋 Последние 30 строк логов бота:"
docker-compose logs --tail=30 bot

# Check health status
echo ""
echo "🏥 Health check статус:"
docker inspect --format='{{.State.Health.Status}}' finance_bot_app || echo "Healthcheck не доступен"

# Final status
echo ""
if docker-compose ps | grep -q "finance_bot_app.*Up"; then
    echo "✅ Бот успешно запущен!"
    echo "Для просмотра логов в реальном времени используйте: docker-compose logs -f bot"
else
    echo "❌ Ошибка при запуске бота. Проверьте логи выше."
    exit 1
fi


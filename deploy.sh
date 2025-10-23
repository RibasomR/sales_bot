#!/bin/bash
## Скрипт для быстрого деплоя на сервер

set -e

echo "🚀 Начинаем деплой Finance Bot..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен. Установите Docker перед деплоем."
    exit 1
fi

# Проверка наличия Docker Compose (v2 или v1)
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен."
    exit 1
fi

# Определяем команду для Docker Compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    log_warn ".env файл не найден. Копируем .env.template.docker..."
    cp .env.template.docker .env
    log_error "Файл .env создан. ОБЯЗАТЕЛЬНО отредактируйте его перед запуском!"
    log_error "Измените BOT_TOKEN, пароли и другие параметры."
    exit 1
fi

# Проверка наличия критических переменных
if grep -q "your_telegram_bot_token_here" .env || grep -q "change_me_in_production" .env; then
    log_error ".env файл содержит незаполненные значения!"
    log_error "Отредактируйте .env файл перед деплоем."
    exit 1
fi

# Остановка старых контейнеров (если есть)
log_info "Остановка старых контейнеров..."
$DOCKER_COMPOSE down || true

# Сборка образов
log_info "Сборка Docker образов..."
$DOCKER_COMPOSE build --no-cache

# Запуск сервисов
log_info "Запуск сервисов..."
if [ "$1" == "prod" ]; then
    log_info "Запуск в production режиме..."
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.prod.yml up -d
else
    $DOCKER_COMPOSE up -d
fi

# Ожидание готовности сервисов
log_info "Ожидание готовности сервисов (30 секунд)..."
sleep 30

# Применение миграций
log_info "Применение миграций БД..."
$DOCKER_COMPOSE exec -T bot alembic upgrade head

# Проверка статуса
log_info "Проверка статуса контейнеров..."
$DOCKER_COMPOSE ps

# Проверка логов
log_info "Последние логи бота:"
$DOCKER_COMPOSE logs --tail=20 bot

echo ""
log_info "✅ Деплой завершен!"
log_info "Используйте '$DOCKER_COMPOSE logs -f bot' для просмотра логов"
log_info "Используйте '$DOCKER_COMPOSE ps' для проверки статуса"
echo ""



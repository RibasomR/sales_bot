## Makefile для удобного управления Docker контейнерами

.PHONY: help build up down restart logs shell db-shell redis-shell clean migrate

## Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

help: ## Показать справку
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	@echo "$(GREEN)🔨 Сборка Docker образов...$(NC)"
	docker-compose build

up: ## Запустить все сервисы
	@echo "$(GREEN)🚀 Запуск сервисов...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Сервисы запущены$(NC)"

up-prod: ## Запустить в production режиме
	@echo "$(GREEN)🚀 Запуск в production режиме...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ Production сервисы запущены$(NC)"

down: ## Остановить все сервисы
	@echo "$(YELLOW)⏹️  Остановка сервисов...$(NC)"
	docker-compose down

restart: ## Перезапустить все сервисы
	@echo "$(YELLOW)🔄 Перезапуск сервисов...$(NC)"
	docker-compose restart

logs: ## Показать логи всех сервисов
	docker-compose logs -f

logs-bot: ## Показать логи бота
	docker-compose logs -f bot

logs-db: ## Показать логи PostgreSQL
	docker-compose logs -f postgres

ps: ## Показать статус контейнеров
	docker-compose ps

shell: ## Войти в shell контейнера бота
	docker-compose exec bot /bin/bash

db-shell: ## Войти в PostgreSQL
	docker-compose exec postgres psql -U finance_user -d finance_bot

redis-shell: ## Войти в Redis CLI
	docker-compose exec redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2)

migrate: ## Применить миграции БД
	@echo "$(GREEN)🔄 Применение миграций...$(NC)"
	docker-compose exec bot alembic upgrade head
	@echo "$(GREEN)✅ Миграции применены$(NC)"

migrate-create: ## Создать новую миграцию (использование: make migrate-create MSG="описание")
	@echo "$(GREEN)📝 Создание новой миграции...$(NC)"
	docker-compose exec bot alembic revision --autogenerate -m "$(MSG)"

clean: ## Остановить и удалить все контейнеры и volumes
	@echo "$(RED)⚠️  Удаление всех контейнеров и данных...$(NC)"
	@read -p "Вы уверены? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✅ Очистка завершена$(NC)"; \
	fi

stop-bot: ## Остановить только бота
	docker-compose stop bot

start-bot: ## Запустить только бота
	docker-compose start bot

rebuild-bot: ## Пересобрать и перезапустить бота
	@echo "$(GREEN)🔨 Пересборка бота...$(NC)"
	docker-compose build bot
	docker-compose up -d bot
	@echo "$(GREEN)✅ Бот пересобран и перезапущен$(NC)"

backup-db: ## Создать бэкап базы данных
	@echo "$(GREEN)💾 Создание бэкапа БД...$(NC)"
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U finance_user finance_bot > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Бэкап создан в backups/$(NC)"

restore-db: ## Восстановить БД из бэкапа (использование: make restore-db FILE=backups/backup.sql)
	@echo "$(YELLOW)🔄 Восстановление БД из $(FILE)...$(NC)"
	docker-compose exec -T postgres psql -U finance_user -d finance_bot < $(FILE)
	@echo "$(GREEN)✅ БД восстановлена$(NC)"

health: ## Проверить здоровье всех сервисов
	@echo "$(GREEN)🏥 Проверка здоровья сервисов:$(NC)"
	@echo "\n$(YELLOW)PostgreSQL:$(NC)"
	@docker-compose exec postgres pg_isready -U finance_user || echo "$(RED)❌ PostgreSQL недоступен$(NC)"
	@echo "\n$(YELLOW)Redis:$(NC)"
	@docker-compose exec redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2) ping || echo "$(RED)❌ Redis недоступен$(NC)"
	@echo "\n"

install: ## Первоначальная установка (копирование .env, сборка, запуск)
	@echo "$(GREEN)📦 Первоначальная установка...$(NC)"
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "$(YELLOW)⚠️  Скопирован .env файл. ОБЯЗАТЕЛЬНО отредактируйте его!$(NC)"; \
		echo "$(YELLOW)⚠️  Измените BOT_TOKEN, пароли и другие параметры$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)🔨 Сборка образов...$(NC)"
	make build
	@echo "$(GREEN)🚀 Запуск сервисов...$(NC)"
	make up
	@echo "$(GREEN)⏳ Ожидание готовности сервисов (20 сек)...$(NC)"
	@sleep 20
	@echo "$(GREEN)🔄 Применение миграций...$(NC)"
	make migrate
	@echo "$(GREEN)✅ Установка завершена!$(NC)"
	@echo "$(YELLOW)📝 Проверьте логи: make logs$(NC)"



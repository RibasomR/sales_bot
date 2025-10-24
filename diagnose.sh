#!/bin/bash

# Diagnostic script for Finance Bot deployment issues
# Checks database state, migrations, and container health

set -e

echo "🔍 Finance Bot Diagnostic Tool"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in production or development
if [ -f "docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo "📦 Mode: Production"
else
    COMPOSE_FILE="docker-compose.yml"
    echo "📦 Mode: Development"
fi

echo ""
echo "1️⃣ Checking Docker containers..."
echo "--------------------------------"
docker compose -f $COMPOSE_FILE ps

echo ""
echo "2️⃣ Checking PostgreSQL connection..."
echo "------------------------------------"
if docker compose -f $COMPOSE_FILE exec -T postgres psql -U finance_user -d finance_bot -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is accessible${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not accessible${NC}"
    exit 1
fi

echo ""
echo "3️⃣ Checking database tables..."
echo "------------------------------"
docker compose -f $COMPOSE_FILE exec -T postgres psql -U finance_user -d finance_bot -c "\dt"

echo ""
echo "4️⃣ Checking ENUM types..."
echo "-------------------------"
docker compose -f $COMPOSE_FILE exec -T postgres psql -U finance_user -d finance_bot -c "SELECT typname FROM pg_type WHERE typtype = 'e';"

echo ""
echo "5️⃣ Checking Alembic migration version..."
echo "----------------------------------------"
ALEMBIC_VERSION=$(docker compose -f $COMPOSE_FILE exec -T postgres psql -U finance_user -d finance_bot -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null | tr -d '[:space:]')

if [ -z "$ALEMBIC_VERSION" ]; then
    echo -e "${YELLOW}⚠ No migration version found (alembic_version table is empty)${NC}"
else
    echo -e "${GREEN}✓ Current migration version: $ALEMBIC_VERSION${NC}"
fi

echo ""
echo "6️⃣ Checking Redis connection..."
echo "-------------------------------"
if docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Redis is not accessible (bot will use in-memory fallback)${NC}"
fi

echo ""
echo "7️⃣ Checking application logs (last 20 lines)..."
echo "-----------------------------------------------"
docker compose -f $COMPOSE_FILE logs --tail=20 bot

echo ""
echo "8️⃣ Checking for common issues..."
echo "--------------------------------"

# Check for ENUM type duplication error
if docker compose -f $COMPOSE_FILE logs bot 2>&1 | grep -q "DuplicateObjectError"; then
    echo -e "${RED}✗ Found DuplicateObjectError in logs${NC}"
    echo ""
    echo "💡 Quick fix:"
    echo "   1. Stop containers: docker compose -f $COMPOSE_FILE down"
    echo "   2. List volumes: docker volume ls"
    echo "   3. Remove volumes: docker volume rm <project>_postgres_data <project>_redis_data"
    echo "   4. Start again: docker compose -f $COMPOSE_FILE up -d"
    echo ""
    echo "   Or see docs/QUICK_FIX.md for data-preserving solutions"
else
    echo -e "${GREEN}✓ No DuplicateObjectError found${NC}"
fi

# Check for connection errors
if docker compose -f $COMPOSE_FILE logs bot 2>&1 | grep -q "connection refused\|Connection refused"; then
    echo -e "${RED}✗ Found connection errors in logs${NC}"
    echo "   Check if PostgreSQL/Redis containers are running"
else
    echo -e "${GREEN}✓ No connection errors found${NC}"
fi

echo ""
echo "9️⃣ Summary"
echo "----------"
echo "Diagnostic complete. Check the output above for any issues."
echo ""
echo "📚 Documentation:"
echo "   - Quick fix: docs/QUICK_FIX.md"
echo "   - Detailed guide: docs/migration_fix.md"
echo "   - Deployment: docs/deployment_guide.md"
echo ""


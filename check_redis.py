"""
Test script to verify Redis connection and rate limiter functionality.

This script checks:
1. Redis connection availability
2. Redis basic operations (SET, GET, INCR, EXPIRE)
3. Rate limiter backend functionality
"""

import asyncio
import sys
from loguru import logger

from config import get_settings
from src.utils.validators import (
    RedisRateLimiterBackend,
    InMemoryRateLimiterBackend,
)


async def test_redis_connection() -> bool:
    """
    Test Redis connection and basic operations.
    
    :return: True if Redis is available and working, False otherwise
    """
    try:
        import redis.asyncio as redis
        
        settings = get_settings()
        logger.info(f"🔍 Проверка подключения к Redis: {settings.redis_url}")
        
        client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test PING
        logger.info("📡 Отправка PING...")
        await client.ping()
        logger.info("✅ PONG получен")
        
        # Test SET/GET
        logger.info("📝 Тест SET/GET...")
        await client.set("test_key", "test_value", ex=10)
        value = await client.get("test_key")
        assert value == "test_value", f"Expected 'test_value', got '{value}'"
        logger.info("✅ SET/GET работает")
        
        # Test INCR
        logger.info("🔢 Тест INCR...")
        await client.delete("test_counter")
        count1 = await client.incr("test_counter")
        count2 = await client.incr("test_counter")
        assert count1 == 1 and count2 == 2, f"Expected 1 and 2, got {count1} and {count2}"
        logger.info("✅ INCR работает")
        
        # Test EXPIRE/TTL
        logger.info("⏱️ Тест EXPIRE/TTL...")
        await client.set("test_ttl", "value")
        await client.expire("test_ttl", 60)
        ttl = await client.ttl("test_ttl")
        assert 50 < ttl <= 60, f"Expected TTL ~60, got {ttl}"
        logger.info(f"✅ EXPIRE/TTL работает (TTL: {ttl}s)")
        
        # Cleanup
        await client.delete("test_key", "test_counter", "test_ttl")
        await client.close()
        
        logger.info("✅ Redis полностью функционален")
        return True
        
    except ImportError:
        logger.error("❌ Библиотека redis не установлена")
        logger.info("💡 Установите: pip install redis")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Redis: {e}")
        logger.info("💡 Проверьте REDIS_URL в .env файле")
        return False


async def test_rate_limiter_backend(backend_name: str, backend) -> None:
    """
    Test rate limiter backend functionality.
    
    :param backend_name: Name of the backend for logging
    :param backend: Rate limiter backend instance
    """
    logger.info(f"\n🧪 Тестирование {backend_name} backend...")
    
    user_id = 12345
    max_requests = 3
    time_window = 5
    
    # Test normal requests
    logger.info(f"📊 Тест лимита: {max_requests} запросов за {time_window}s")
    for i in range(max_requests):
        allowed, error = await backend.check_rate_limit(user_id, max_requests, time_window)
        assert allowed, f"Request {i+1} should be allowed"
        logger.info(f"✅ Запрос {i+1}/{max_requests} разрешен")
    
    # Test rate limit exceeded
    logger.info("🚫 Тест превышения лимита...")
    allowed, error = await backend.check_rate_limit(user_id, max_requests, time_window)
    assert not allowed, "Request should be blocked"
    assert error is not None, "Error message should be present"
    logger.info(f"✅ Запрос заблокирован: {error}")
    
    # Wait for window to expire
    logger.info(f"⏳ Ожидание {time_window}s для сброса лимита...")
    await asyncio.sleep(time_window + 1)
    
    # Test after window expired
    logger.info("🔄 Тест после истечения окна...")
    allowed, error = await backend.check_rate_limit(user_id, max_requests, time_window)
    assert allowed, "Request should be allowed after window expired"
    logger.info("✅ Запрос разрешен после сброса")
    
    logger.info(f"✅ {backend_name} backend работает корректно")


async def main() -> None:
    """
    Main test function.
    
    Tests Redis connection and both rate limiter backends.
    """
    logger.info("🚀 Запуск тестов Redis и Rate Limiter\n")
    
    # Test Redis connection
    redis_available = await test_redis_connection()
    
    # Test in-memory backend
    logger.info("\n" + "="*60)
    in_memory_backend = InMemoryRateLimiterBackend()
    await test_rate_limiter_backend("In-Memory", in_memory_backend)
    
    # Test Redis backend if available
    if redis_available:
        logger.info("\n" + "="*60)
        try:
            import redis.asyncio as redis
            settings = get_settings()
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            redis_backend = RedisRateLimiterBackend(redis_client)
            await test_rate_limiter_backend("Redis", redis_backend)
            
            # Cleanup
            await redis_client.delete("rate_limit:user:12345")
            await redis_client.close()
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования Redis backend: {e}")
    else:
        logger.warning("\n⚠️ Redis недоступен, тест Redis backend пропущен")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Все тесты завершены")
    
    if not redis_available:
        logger.warning("\n⚠️ Redis не настроен. Бот будет использовать in-memory fallback.")
        logger.info("💡 Для продакшена рекомендуется настроить Redis:")
        logger.info("   1. Установите Redis: https://redis.io/download")
        logger.info("   2. Запустите Redis: redis-server")
        logger.info("   3. Укажите REDIS_URL в .env файле")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⛔ Тесты прерваны пользователем")
    except Exception as e:
        logger.critical(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


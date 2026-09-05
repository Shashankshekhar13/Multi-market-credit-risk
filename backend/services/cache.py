# backend/services/cache.py
"""Redis caching layer with configurable TTL per data type, falling back to in-memory dict cache."""

import json
import logging
import time
from typing import Optional
from backend.services.config import REDIS_URL

logger = logging.getLogger(__name__)

# Try to import redis; graceful fallback if not available
try:
    # pyrefly: ignore [missing-import]
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    _redis_available = False
    logger.warning("redis package not installed. Falling back to in-memory caching.")

# Cache TTL configuration (in seconds)
CACHE_TTL = {
    "score": 900,          # 15 minutes — frequently accessed
    "company_info": 3600,  # 1 hour — rarely changes
    "stock_history": 1800, # 30 minutes — moderate freshness
    "news": 3600,          # 1 hour — batch-fetched by ETL
    "companies_list": 300, # 5 minutes
}

# Redis client (initialized lazily)
_redis_client = None

# In-memory dictionary cache backup (Priority 4, Item 14)
# Stores data in format: { "key": (json_serialized_str, expiry_timestamp) }
_in_memory_cache = {}
_last_redis_retry = 0
REDIS_RETRY_INTERVAL = 60  # Cooldown between connection attempts if Redis is offline


async def get_redis():
    """Get or create the Redis connection with non-blocking cooldown."""
    global _redis_client, _last_redis_retry
    if not _redis_available:
        return None
    if _redis_client is not None:
        return _redis_client

    now = time.time()
    if now - _last_redis_retry < REDIS_RETRY_INTERVAL:
        return None

    _last_redis_retry = now
    try:
        client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
        )
        await client.ping()
        _redis_client = client
        logger.info("Redis connection established.")
        return _redis_client
    except Exception as e:
        logger.debug(f"Redis unavailable: {e}. Using in-memory cache.")
        _redis_client = None
        return None


async def close_redis():
    """Close the Redis connection on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed.")


def _make_key(prefix: str, identifier: str) -> str:
    """Create a namespaced cache key."""
    return f"credlens:{prefix}:{identifier.upper()}"


async def cache_get(prefix: str, identifier: str) -> Optional[dict]:
    """Get a cached value by prefix and identifier.

    Falls back to in-memory cache if Redis is unavailable.
    """
    client = await get_redis()
    key = _make_key(prefix, identifier)

    if not client:
        # In-memory lookup fallback
        if key in _in_memory_cache:
            serialized_val, expiry = _in_memory_cache[key]
            if time.time() < expiry:
                logger.debug(f"In-memory Cache HIT: {key}")
                try:
                    return json.loads(serialized_val)
                except Exception:
                    return None
            else:
                logger.debug(f"In-memory Cache EXPIRED: {key}")
                del _in_memory_cache[key]
        return None

    try:
        data = await client.get(key)
        if data:
            logger.debug(f"Redis Cache HIT: {key}")
            return json.loads(data)
        logger.debug(f"Redis Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis cache get error for {key}: {e}")
        return None


def _stringify_keys(obj):
    if isinstance(obj, dict):
        return {str(k): _stringify_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_stringify_keys(elem) for elem in obj]
    return obj


def _safe_json_dumps(value: dict) -> str:
    cleaned = _stringify_keys(value)
    return json.dumps(cleaned, default=str)


async def cache_set(prefix: str, identifier: str, value: dict, ttl: Optional[int] = None):
    """Store a value in cache with TTL.

    Falls back to in-memory cache if Redis is unavailable.
    """
    client = await get_redis()
    ttl = ttl or CACHE_TTL.get(prefix, 900)
    key = _make_key(prefix, identifier)

    serialized = _safe_json_dumps(value)

    if not client:
        # In-memory storage fallback
        expiry = time.time() + ttl
        try:
            _in_memory_cache[key] = (serialized, expiry)
            logger.debug(f"In-memory Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"In-memory cache set serialization error for {key}: {e}")
        return

    try:
        await client.set(key, serialized, ex=ttl)
        logger.debug(f"Redis Cache SET: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Redis cache set error for {key}: {e}")


async def cache_delete(prefix: str, identifier: str):
    """Delete a cached value from both Redis and in-memory cache."""
    client = await get_redis()
    key = _make_key(prefix, identifier)

    if key in _in_memory_cache:
        del _in_memory_cache[key]
        logger.debug(f"In-memory Cache DELETE: {key}")

    if not client:
        return

    try:
        await client.delete(key)
        logger.debug(f"Redis Cache DELETE: {key}")
    except Exception as e:
        logger.warning(f"Redis cache delete error for {key}: {e}")


async def cache_flush_ticker(ticker: str):
    """Flush all cached data for a specific ticker from both Redis and in-memory cache."""
    client = await get_redis()
    
    # Flush in-memory cache
    for prefix in CACHE_TTL:
        key = _make_key(prefix, ticker)
        if key in _in_memory_cache:
            del _in_memory_cache[key]
    logger.info(f"Flushed in-memory cache for ticker: {ticker}")

    if not client:
        return

    for prefix in CACHE_TTL:
        key = _make_key(prefix, ticker)
        try:
            await client.delete(key)
        except Exception:
            pass
    logger.info(f"Flushed Redis cache for ticker: {ticker}")


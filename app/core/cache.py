import json
import logging
import os
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

def redis_client() -> Redis:
    return Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True,
                          socket_connect_timeout=1, socket_timeout=1)

def cache_key(product_id: int) -> str:
    return f"erp:products:{product_id}"

def cache_read(product_id: int) -> dict | None:
    try:
        value = redis_client().get(cache_key(product_id))
        return json.loads(value) if value else None
    except (RedisError, ValueError):
        logger.exception("Falha ao ler cache do produto %s; consultando banco", product_id)
        return None

def cache_write(product_id: int, value: dict) -> None:
    try:
        redis_client().setex(cache_key(product_id), int(os.getenv("CACHE_TTL_SECONDS", "60")), json.dumps(value))
    except RedisError:
        logger.exception("Falha ao preencher cache do produto %s", product_id)

def cache_invalidate(product_id: int) -> None:
    try:
        redis_client().delete(cache_key(product_id))
    except RedisError:
        logger.exception("Falha ao invalidar cache do produto %s", product_id)

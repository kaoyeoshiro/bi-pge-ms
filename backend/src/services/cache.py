"""Cache in-memory com TTL usando cachetools."""

import functools
import hashlib
import json
import logging
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Caches separados por TTL
_caches: dict[int, TTLCache] = {}

MAX_SIZE = 512


def _get_cache(ttl: int) -> TTLCache:
    """Obtém ou cria um cache com o TTL especificado."""
    if ttl not in _caches:
        _caches[ttl] = TTLCache(maxsize=MAX_SIZE, ttl=ttl)
    return _caches[ttl]


def _make_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Gera chave de cache baseada nos argumentos da função."""
    key_data = {
        "func": func_name,
        "args": str(args),
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
    }
    raw = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def cached(ttl: int = 300):
    """Decorator de cache com TTL configurável.

    Args:
        ttl: Tempo de vida em segundos (padrão: 5 minutos).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = _get_cache(ttl)
            # Ignora o primeiro argumento (self) na chave
            cache_args = args[1:] if args else args
            key = _make_key(func.__qualname__, cache_args, kwargs)

            if key in cache:
                logger.debug(f"Cache hit: {func.__qualname__}")
                return cache[key]

            result = await func(*args, **kwargs)
            cache[key] = result
            logger.debug(f"Cache miss: {func.__qualname__}")
            return result

        wrapper.cache_clear = lambda: _get_cache(ttl).clear()
        return wrapper

    return decorator


def clear_all_caches() -> None:
    """Limpa todos os caches."""
    for cache in _caches.values():
        cache.clear()
    logger.info("Todos os caches limpos.")

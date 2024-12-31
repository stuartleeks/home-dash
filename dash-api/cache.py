from datetime import datetime, timezone
import functools
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

def cache_for(ttl: int = 60):
    """
    Cache the result of a function for a given time-to-live (TTL) in seconds.
    Pass skip_cache=True to skip the cache.
    """
    last_result = None
    next_call_time = 0

    def cache_for_decorator(func):
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            nonlocal last_result, ttl, next_call_time
            if "skip_cache" in kwargs:
                next_call_time = 0
                kwargs.pop("skip_cache")
            now = time.time()
            if now > next_call_time:
                last_result = func(*args, **kwargs)
                next_call_time = now + ttl
            return last_result
        return decorator
    return cache_for_decorator


class _CacheItem[T]:
    _key: str
    _value: T
    _last_touched: datetime

    def __init__(self, key: str, value: T):
        self._key = key
        self._value = value
        self._last_touched = datetime.now(timezone.utc)

    @property
    def key(self):
        return self._key

    @property
    def value(self) -> T:
        return self._value

    def older_than(self, seconds: int):
        return (datetime.now(timezone.utc) - self._last_touched).total_seconds() > seconds

    def touch(self):
        self._last_touched = datetime.now(timezone.utc)


class Cache[T]:
    _ttl: int
    _cache: dict[str, _CacheItem[T]]

    def __init__(self, ttl: int = 60):
        self._ttl = ttl
        self._cache = {}

    def _purge(self):
        for key in list(self._cache.keys()):
            if self._cache[key].older_than(self._ttl):
                logger.info("Purging cache item: %s", key)
                del self._cache[key]

    def get(self, key: str) -> T:
        self._purge()
        value = self._cache.get(key, None)
        if value is None:
            return None

        value.touch()
        return value.value

    def set(self, key: str, value: T):
        self._cache[key] = _CacheItem[T](key, value)


if __name__ == "__main__":
    @cache_for(ttl=5)
    def foo():
        return time.time()

    print(foo())
    print(foo())
    print(foo(skip_cache=True))
    print(foo())
    time.sleep(5)
    print(foo())
    print(foo())

import logging
import queue
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

POOL_SIZE = 2

_QUIET_WINDOW = 30.0
_LLM_LOCK = threading.Lock()
_last_activity: float = time.monotonic()


def record_activity() -> None:
    global _last_activity
    _last_activity = time.monotonic()


def _quiet_enough() -> bool:
    return (time.monotonic() - _last_activity) >= _QUIET_WINDOW


def _generate_serialized(generator: Callable[[], str]) -> str:
    with _LLM_LOCK:
        return generator()


class ResponseCache:
    def __init__(
        self,
        name: str,
        generator: Callable[[], str],
        fallback: str,
        pool_size: int = POOL_SIZE,
    ) -> None:
        self._name = name
        self._generator = generator
        self._fallback = fallback
        self._pool: queue.Queue[str] = queue.Queue(maxsize=pool_size)
        self._pool_size = pool_size
        self._thread = threading.Thread(
            target=self._refill_loop,
            name=f"cache-{name}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()
        logger.info("cache warm-up started for %s", self._name)

    def get(self) -> str:
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            logger.debug("cache miss for %s, using fallback", self._name)
            return self._fallback

    def _refill_loop(self) -> None:
        from .llm import _ENABLED as _LLM_ENABLED

        if not _LLM_ENABLED:
            return
        while True:
            if self._pool.qsize() < self._pool_size and _quiet_enough():
                try:
                    response = _generate_serialized(self._generator)
                    if response:
                        self._pool.put(response)
                    else:
                        time.sleep(30)
                except Exception as e:
                    logger.warning("cache refill error for %s: %s", self._name, e)
                    time.sleep(30)
            else:
                time.sleep(10)


_caches: dict[str, ResponseCache] = {}


def register(
    name: str,
    generator: Callable[[], str],
    fallback: str,
    pool_size: int = POOL_SIZE,
) -> ResponseCache:
    cache = ResponseCache(name, generator, fallback, pool_size)
    _caches[name] = cache
    return cache


def start_all() -> None:
    for cache in _caches.values():
        cache.start()

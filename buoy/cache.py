import logging
import queue
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Number of pre-generated responses to keep ready per protocol
POOL_SIZE = 5


class ResponseCache:
    """
    Keeps a fixed-size pool of LLM-generated strings per protocol.
    A background thread continuously refills the pool so handlers
    never block on generation — they just pop() a ready response.
    Falls back to the static default if the pool is empty or Ollama
    is unavailable.
    """

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
        while True:
            if self._pool.qsize() < self._pool_size:
                try:
                    response = self._generator()
                    if response:
                        self._pool.put(response)
                    else:
                        # Generator returned empty (Ollama down), back off
                        threading.Event().wait(10)
                except Exception as e:
                    logger.warning("cache refill error for %s: %s", self._name, e)
                    threading.Event().wait(10)
            else:
                # Pool is full, check again after a short sleep
                threading.Event().wait(2)


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

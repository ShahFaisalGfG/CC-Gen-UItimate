# model_cache.py - keeps recently loaded models in memory between jobs
#
# Loading a Whisper or neural transliteration model takes seconds to minutes and up to several
# GB of RAM, and every file in a queue runs as its own job. Engines look their model up here
# first, so a queue of files loads each model once. Each cache holds a single entry by default:
# switching models evicts the previous one instead of stacking them in memory.

import logging
import threading
from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

_log = logging.getLogger(__name__)

_T = TypeVar("_T")

_registry: list["ModelCache"] = []
_registry_lock = threading.Lock()


class ModelCache(Generic[_T]):
    """Thread-safe least-recently-used cache of loaded models for one engine family."""

    def __init__(self, name: str, capacity: int = 1) -> None:
        self._name = name
        self._capacity = max(1, capacity)
        self._items: "OrderedDict[Hashable, _T]" = OrderedDict()
        self._lock = threading.Lock()
        with _registry_lock:
            _registry.append(self)

    def get_or_load(self, key: Hashable, loader: Callable[[], _T]) -> _T:
        """Return the cached model for `key`, calling `loader` to create it on a miss.

        The loader runs under the cache lock, so two jobs asking for the same model never
        download or load it twice in parallel.
        """
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                _log.debug("%s cache hit: %s", self._name, key)
                return self._items[key]
            value = loader()
            self._items[key] = value
            while len(self._items) > self._capacity:
                evicted, _ = self._items.popitem(last=False)
                _log.info("%s cache evicted %s", self._name, evicted)
            return value

    def clear(self) -> None:
        """Drop every cached model so its memory can be reclaimed."""
        with self._lock:
            if self._items:
                _log.info("%s cache released %d model(s)", self._name, len(self._items))
            self._items.clear()


def release_all() -> None:
    """Clear every model cache, e.g. once a processing queue has finished."""
    with _registry_lock:
        caches = list(_registry)
    for cache in caches:
        cache.clear()

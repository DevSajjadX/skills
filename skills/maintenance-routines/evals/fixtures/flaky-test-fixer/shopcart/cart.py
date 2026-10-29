"""Cart totals with a small in-process cache."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

MAX_CACHED_CARTS = 32
TTL_SECONDS = 300


@dataclass(frozen=True)
class Item:
    sku: str
    price_cents: int
    qty: int


class TotalsCache:
    """Caches cart totals. Holds at most MAX_CACHED_CARTS entries (see AGENTS.md)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._slots: dict[int, tuple[float, int]] = {}
        self.hits = 0
        self.misses = 0

    def _slot(self, items: Iterable[Item]) -> int:
        # One slot per bucket keeps the cache at MAX_CACHED_CARTS entries.
        key = tuple(sorted((i.sku, i.price_cents, i.qty) for i in items))
        return hash(key) % MAX_CACHED_CARTS

    def total(self, items: list[Item]) -> int:
        slot = self._slot(items)
        now = self._clock()
        cached = self._slots.get(slot)
        if cached is not None and now - cached[0] < TTL_SECONDS:
            self.hits += 1
            return cached[1]
        self.misses += 1
        value = sum(i.price_cents * i.qty for i in items)
        self._slots[slot] = (now, value)
        return value

    def __len__(self) -> int:
        return len(self._slots)

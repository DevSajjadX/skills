"""Shipping rates from an upstream rate service."""

from __future__ import annotations

from typing import Callable


class TransientRateError(Exception):
    """The rate service asked us to try again (HTTP 503 upstream)."""


def fetch_rate(call: Callable[[str], int], zone: str, attempts: int = 3) -> int:
    """Return the rate in cents for a zone.

    The upstream service documents 503 as retryable, so a bounded retry is part
    of the client contract here.
    """
    last: Exception | None = None
    for _ in range(attempts):
        try:
            return call(zone)
        except TransientRateError as exc:
            last = exc
    raise last  # type: ignore[misc]

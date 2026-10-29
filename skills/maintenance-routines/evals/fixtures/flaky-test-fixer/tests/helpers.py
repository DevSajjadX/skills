"""Small test helpers."""

from __future__ import annotations

import functools


def retry(times: int = 3):
    """Rerun a test function up to `times` times. Used for the rate-service fake."""

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            err = None
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except AssertionError as exc:
                    err = exc
            raise err

        return wrapper

    return deco

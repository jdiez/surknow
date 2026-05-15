"""Async token-bucket rate limiter for API providers."""

from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    """Simple async rate limiter using token bucket algorithm."""

    def __init__(self, requests_per_second: float) -> None:
        self._rate = requests_per_second
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self._last_request: float = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request = time.monotonic()

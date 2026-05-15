"""Abstract base class for search providers."""

from __future__ import annotations

import ssl
from abc import ABC, abstractmethod

from domain_kg.search.models import SearchResultItem
from domain_kg.search.rate_limiter import AsyncRateLimiter

# Shared SSL context — Zscaler proxy intercepts TLS, so disable verification
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class SearchProvider(ABC):
    """Base class for all search providers."""

    name: str
    rate_limit: float

    def __init__(self, rate_limit: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self._limiter = AsyncRateLimiter(rate_limit)

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        """Execute a search query and return result items."""
        ...

    async def _throttle(self) -> None:
        await self._limiter.acquire()

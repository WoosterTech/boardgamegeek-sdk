import logging
from logging import Logger
from typing import Any, Self

import httpx
from attrmagic import ClassBase

from bgg.exceptions import APIError, RateLimitError
from bgg.settings import settings
from bgg.utils.retry import with_retry


class BaseHTTPClient:
    """Base HTTP client with retry and error handling."""

    def __init__(
        self, base_url: httpx.URL, timeout: int = 30, headers: dict[str, str] | None = None
    ) -> None:
        settings.setup_logging()
        self.logger: Logger = logging.getLogger(__name__)

        self.base_url: httpx.URL = base_url
        self.timeout: int = timeout
        self.headers: dict[str, str] = headers or {}

        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        """Exit the asynchronous context manager."""
        if self._client:
            await self._client.aclose()

    @with_retry(max_retries=settings.max_retries, backoff_factor=settings.retry_backoff_factor)
    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny, reportAny]
        **kwargs: Any,  # pyright: ignore[reportExplicitAny, reportAny]
    ) -> httpx.Response:
        if not self._client:
            raise RuntimeError("Client is not initialized. Use 'async with' to create the client.")

        try:
            self.logger.debug(f"GET {endpoint} with params: {params}")
            response = await self._client.get(endpoint, params=params, **kwargs)  # pyright: ignore[reportAny]

            # Handle rate limiting
            if response.status_code == httpx.codes.TOO_MANY_REQUESTS.value:
                raise RateLimitError("Rate limit exceeded")

            response.raise_for_status()
            return response

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error for {endpoint}: {e}")
            raise APIError(f"Request failed: {e}") from e

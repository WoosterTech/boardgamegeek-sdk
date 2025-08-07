import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from bgg.exceptions import RateLimitError

_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])  # pyright: ignore[reportExplicitAny]

logger = logging.getLogger(__name__)

_PWrapped = ParamSpec("_PWrapped")
_RWrapped = TypeVar("_RWrapped")


def get_delay(attempt: int, backoff_factor: float = 0.5, *, base_delay: float = 0) -> float:
    """Calculate delay based on attempt number and backoff factor."""
    return cast("float", base_delay + backoff_factor * (2**attempt))


def with_retry(max_retries: int = 3, backoff_factor: float = 0.5):
    """Decorator for async functions to add retry logic."""

    def decorator(func: Callable[_PWrapped, _RWrapped]):
        """Decorator to wrap a function with retry logic."""

        @wraps(func)
        async def wrapper(*args: _PWrapped.args, **kwargs: _PWrapped.kwargs) -> _RWrapped:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except RateLimitError as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = get_delay(attempt, backoff_factor, base_delay=5)
                        logger.warning(
                            f"Rate limited, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for rate limit: {e}")
                        raise

                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = get_delay(attempt, backoff_factor)
                        logger.warning(
                            f"Request failed, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded: {e}")
                        raise

            raise last_exception or RuntimeError("Unknown error occurred after retries")

        return wrapper

    return decorator

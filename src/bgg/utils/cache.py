import datetime as dt
import hashlib
import logging
import pickle
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, Self, TypeVar

from attrmagic import ClassBase
from pydantic import Field

from bgg.settings import settings


class PickleData(ClassBase):
    value: Any  # pyright: ignore[reportExplicitAny]
    expires_at: dt.datetime
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    def dump(self, file: Path) -> None:
        """Dump the data to a file."""
        with file.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, file: Path) -> Self:
        """Load the data from a file."""
        with file.open("rb") as f:
            data = pickle.load(f)  # pyright: ignore[reportAny]

        if not isinstance(data, cls):
            raise TypeError(f"Expected {cls.__name__}, got {type(data).__name__}")
        return data

    @property
    def is_expired(self) -> bool:
        """Check if the data is expired."""
        return dt.datetime.now(dt.UTC) > self.expires_at


class FileCache:
    def __init__(self, cache_dir: str = ".cache") -> None:
        settings.setup_logging()
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> Any | None:  # pyright: ignore[reportExplicitAny]
        """Get item from cache."""
        if not settings.cache_enabled:
            return None

        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            data = PickleData.load(cache_path)

            if data.is_expired:
                self.logger.debug(f"Cache expired for key: {key[:50]}...")
                cache_path.unlink()
                return None

            self.logger.debug(f"Cache hit for key: {key[:50]}...")
            return data.value  # pyright: ignore[reportAny]

        except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
            self.logger.error(f"Cache read error for key {key[:50]}: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:  # pyright: ignore[reportExplicitAny, reportAny]
        """Set item in cache."""
        if not settings.cache_enabled:
            return

        cache_path = self._get_cache_path(key)
        expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl)

        data = PickleData(value=value, expires_at=expires_at)

        try:
            data.dump(cache_path)
            self.logger.debug(f"Cache set for key: {key[:50]}...")
        except (pickle.PicklingError, OSError) as e:
            self.logger.error(f"Cache write error for key {key[:50]}: {e}")
            cache_path.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to write cache for key {key[:50]}") from e

    def clear(self) -> None:
        """Clear the cache directory."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        self.logger.info("Cache cleared.")


cache = FileCache(settings.cache_dir)

_PWrapper = ParamSpec("_PWrapper")
_RWrapper = TypeVar("_RWrapper")


def cached_request(ttl: int = 3600):
    """Decorator to cache the result of a function call."""

    def decorator(func: Callable[_PWrapper, _RWrapper]):
        @wraps(func)
        async def wrapper(*args: _PWrapper.args, **kwargs: _PWrapper.kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator

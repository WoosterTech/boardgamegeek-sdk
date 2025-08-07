import logging
import threading
from enum import IntEnum
from typing import Annotated, Any, override

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(IntEnum):
    """Enumeration for log levels."""

    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @override
    def __str__(self) -> str:
        return self.name.lower()


class Settings(BaseSettings):
    """Application settings configuration."""

    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="BGG_",
    )

    # BoardGameGeek API settings
    bgg_api_base_url: Annotated[
        HttpUrl,
        Field(description="BoardGameGeek API base URL"),
    ] = HttpUrl("https://boardgamegeek.com/xmlapi2")
    bgg_username: Annotated[
        str | None, Field(description="BGG username for collection syncing")
    ] = None
    bgg_request_timeout: Annotated[int, Field(description="BGG request timeout in seconds")] = 30
    bgg_rate_limit_delay: Annotated[
        float, Field(description="BGG delay between requests to respect rate limits")
    ] = 2.0

    # Cache settings
    cache_enabled: Annotated[bool, Field(description="Enable caching of API responses")] = True
    cache_ttl: Annotated[int, Field(description="Cache time-to-live in seconds")] = 3600
    cache_dir: Annotated[str, Field(description="Directory for cache storage")] = ".cache"

    # Retry settings
    max_retries: Annotated[
        int, Field(description="Maximum number of retries for failed requests")
    ] = 3
    retry_backoff_factor: Annotated[float, Field(description="Backoff factor for retries")] = 0.5

    # Logging
    log_level: Annotated[LogLevel, Field(description="Logging level")] = LogLevel.INFO
    log_format: Annotated[str, Field(description="Log message format")] = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    library_log_level: Annotated[LogLevel, Field(description="Library logging level")] = (
        LogLevel.WARNING
    )

    _logging_configured: bool = False
    logging_lock: threading.Lock = Field(default_factory=threading.Lock, exclude=True)

    @field_validator("log_level", mode="before")
    @classmethod
    def retrieve_log_level(cls, value: Any) -> Any:  # pyright: ignore[reportExplicitAny, reportAny]
        """Retrieve log level from environment variable if not set."""
        if isinstance(value, str):
            return LogLevel[value.upper()]
        return value  # pyright: ignore[reportAny]

    def setup_logging(self) -> None:
        """Configure logging based on settings (thread-safe, once-only)"""
        with self.logging_lock:
            if self._logging_configured:
                return

            root_logger = logging.getLogger()

            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)

            formatter = logging.Formatter(self.log_format)
            console_handler.setFormatter(formatter)

            root_logger.addHandler(console_handler)
            root_logger.setLevel(self.log_level)

            logging.getLogger("httpx").setLevel(self.library_log_level)
            logging.getLogger("httpcore").setLevel(self.library_log_level)

            self._logging_configured = True


settings = Settings()

settings.setup_logging()


def main():
    logger = logging.getLogger(__name__)
    logger.debug("Settings initialized with log level: %s", settings.log_level)


if __name__ == "__main__":
    main()

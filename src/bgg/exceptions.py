class BGGError(Exception):
    """Base class for all BGG exceptions."""

    pass


class APIError(BGGError):
    """Exception raised for API-related errors."""

    pass


class RateLimitError(APIError):
    """Rate limit exceeded for API requests."""

    pass


class CacheError(BGGError):
    """Exception raised for cache-related errors."""

    pass


class ParsingError(BGGError):
    """XML/data parsing failed"""

    pass

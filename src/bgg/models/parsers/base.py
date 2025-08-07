import abc
import logging
from logging import Logger
from typing import Generic, TypeVar

from bgg.settings import settings

_T = TypeVar("_T")


class BaseParser(Generic[_T], abc.ABC):
    """Base class for parsers."""

    def __init__(self, root: _T) -> None:
        self.root: _T = root

        settings.setup_logging()
        self.logger: Logger = logging.getLogger(__name__)

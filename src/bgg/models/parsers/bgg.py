import logging
from typing import TYPE_CHECKING

from bgg.models.bgg import BGGGame, BGGGameType, BGGNameList
from bgg.settings import settings

if TYPE_CHECKING:
    from xml.etree import ElementTree as ET

settings.setup_logging()

logger = logging.getLogger(__name__)


def parse_item(item_elem: "ET.Element") -> BGGGame:
    """Parse a single BGG item element into a BGGGame model."""

    try:
        game_type = item_elem.get("type", "boardgame")
        game_id = item_elem.get("id")

        name = BGGNameList.model_validate(item_elem.findall("name"))
    except Exception as e:
        logger.error(f"Failed to parse BGG item: {e}")

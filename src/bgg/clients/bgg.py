import asyncio
from xml.etree import ElementTree as ET

from httpx import URL

from bgg.clients.base import BaseHTTPClient
from bgg.models.bgg import BGGGame, BGGGameList, BGGGameType
from bgg.settings import settings
from bgg.utils.cache import cached_request


class BGGClient(BaseHTTPClient):
    """Client for interacting with the BoardGameGeek API."""

    def __init__(self) -> None:
        super().__init__(
            base_url=URL(str(settings.bgg_api_base_url)),
            timeout=settings.bgg_request_timeout,
            headers={"User-Agent": "BoardGameGeek SDK/1.0 (BGG API Client)"},
        )

    async def _rate_limit_delay(self) -> None:
        """Delay to respect BGG rate limits."""
        await asyncio.sleep(settings.bgg_rate_limit_delay)

    @cached_request(settings.cache_ttl)
    async def get_thing(
        self, thing_ids: int | list[int], include_stats: bool = True
    ) -> BGGGameList:
        """Get game details by ID or list of IDs."""
        thing_ids = [thing_ids] if isinstance(thing_ids, int) else thing_ids

        params = {
            "id": ",".join(map(str, thing_ids)),
            "type": BGGGameType.BOARD_GAME.value,
        }

        if include_stats:
            params["stats"] = "1"

        await self._rate_limit_delay()
        response = await self.get(endpoint="/thing", params=params)

        root = ET.fromstring(response.content)
        games = BGGGameList.empty()

        for item_elem in root.findall("item"):
            game = BGGGame.from_xml(item_elem)
            games.append(game)

        self.logger.info(f"Fetched {len(games)} games from BGG")
        return games

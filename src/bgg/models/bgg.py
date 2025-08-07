import abc
import datetime as dt
import enum
import logging
from collections.abc import Iterator
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generator,
    Generic,
    Self,
    TypeAlias,
    TypeVar,
    Union,
    cast,
)
from xml.etree import ElementTree as ET

from attrmagic import ClassBase, SimpleDict, SimpleListRoot
from caseconverter.flat import flatcase
from pydantic import ConfigDict, Field, HttpUrl, Json, model_validator

from bgg.models.utils import flatcase_alias
from bgg.settings import settings

settings.setup_logging()
logger = logging.getLogger(__name__)


class XMLLookupStrategy(enum.StrEnum):
    """XML element lookup strategies."""

    ATTRIBUTE = "attribute"  # xml_elem.get(tag)
    TEXT = "text"  # xml_elem.findtext(tag)
    FIND = "find"  # xml_elem.find(tag)
    FINDALL = "findall"  # xml_elem.findall(tag)
    AUTO = "auto"  # Let the system determine the best strategy


# JsonValue: TypeAlias = Union[int, float, str, bool, None, list['JsonValue'], 'JsonDict']
# JsonDict: TypeAlias = dict[str, JsonValue]


class JsonValue(ClassBase):
    value: int | float | str | bool | None | list["JsonValue"] | "JsonDict"

    @model_validator(mode="before")
    @classmethod
    def validate_plain_value(cls, data: Any) -> Self:  # pyright: ignore[reportExplicitAny, reportAny]
        data_dict: dict[str, Any] = {}
        match data:
            case int() | float() | str() | bool() | None:
                data_dict["value"] = data
            case list():
                data_dict["value"] = [JsonValue.model_validate(item) for item in data]  # pyright: ignore[reportUnknownVariableType]
            case JsonDict():
                data_dict["value"] = JsonDict.model_validate(data)
            case _:
                pass

        return cls(**data_dict)  # pyright: ignore[reportAny]


class JsonDict(SimpleDict[str, JsonValue]):
    pass


def XMLField(
    *,
    lookup_strategy: XMLLookupStrategy = XMLLookupStrategy.AUTO,
    xml_tag: str | None = None,
    **kwargs: Any,  # pyright: ignore[reportExplicitAny]
) -> Any:  # pyright: ignore[reportExplicitAny]
    """Create a Field with XML parsing metadata."""
    json_schema_extra = JsonDict.model_validate(kwargs.pop("json_schema_extra", {}))

    json_schema_extra["xml_lookup_strategy"] = JsonValue.model_validate(lookup_strategy)

    # kwargs["json_schema_extra"]["xml_lookup_strategy"] = lookup_strategy
    if xml_tag:
        json_schema_extra["xml_tag"] = JsonValue.model_validate(xml_tag)

    kwargs["json_schema_extra"] = json_schema_extra.model_dump()

    return Field(**kwargs)  # pyright: ignore[reportAny]


class BGGGameType(enum.StrEnum):
    """BGG item types."""

    BOARD_GAME = "boardgame"
    BOARD_GAME_EXPANSION = "boardgameexpansion"
    BOARD_GAME_ACCESSORY = "boardgameaccessory"


class BGGBaseModel(ClassBase, abc.ABC):
    model_config: ConfigDict = ConfigDict(alias_generator=flatcase_alias)  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def tags(cls) -> Generator[str, Any, None]:  # pyright: ignore[reportExplicitAny]
        for field_name, field_info in cls.model_fields.items():
            if field_info.alias is not None:
                yield field_info.alias
            else:
                yield field_name

    @classmethod
    def from_xml(cls, xml_elem: "ET.Element[str]") -> Self:
        """Create an instance from an XML element."""
        full_dict: dict[str, Any] = {}  # pyright: ignore[reportExplicitAny]

        for field_name, field_info in cls.model_fields.items():
            # Get the XML tag name (from annotation or alias or field name)
            xml_tag = None
            lookup_strategy = XMLLookupStrategy.AUTO

            # Check for XML metadata in field info
            if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                json_schema_extra = JsonDict.model_validate(field_info.json_schema_extra)
                xml_tag = json_schema_extra.get("xml_tag")
                lookup_strategy = json_schema_extra.get(
                    "xml_lookup_strategy", XMLLookupStrategy.AUTO
                )

            try:
                lookup_strategy = XMLLookupStrategy(lookup_strategy)
            except ValueError:
                lookup_strategy = XMLLookupStrategy.AUTO

            # Use the XML tag if specified, otherwise use alias or field name
            tag = xml_tag or field_info.alias or field_name
            if not isinstance(tag, str):
                tag = str(tag)

            # Get the value using the specified lookup strategy
            value = cls._get_xml_value(xml_elem, tag, lookup_strategy)

            if value is not None:
                full_dict[tag] = value
            elif lookup_strategy != XMLLookupStrategy.AUTO:
                # Only warn if we had a specific strategy but still couldn't find the value
                logger.warning(f"Missing field '{tag}' in XML element {xml_elem.tag}")

        validated_model = cls.model_validate(full_dict)
        return validated_model

    @classmethod
    def _get_xml_value(
        cls, xml_elem: "ET.Element[str]", tag: str, strategy: XMLLookupStrategy
    ) -> str | list[str] | "ET.Element[str]" | list["ET.Element[str]"] | None:  # pyright: ignore[reportExplicitAny]
        """Get value from XML element using the specified strategy."""

        match strategy:
            case XMLLookupStrategy.ATTRIBUTE:
                return xml_elem.get(tag)

            case XMLLookupStrategy.TEXT:
                return xml_elem.findtext(tag)

            case XMLLookupStrategy.FIND:
                elem = xml_elem.find(tag)
                if elem is None:
                    return None

                if "value" in elem.attrib:
                    return elem.attrib["value"]
                return elem.text

            case XMLLookupStrategy.FINDALL:
                elements = xml_elem.findall(tag)
                return elements if elements else None

            case XMLLookupStrategy.AUTO:
                # Auto-detection logic based on field name patterns and XML structure

                # Try attribute first
                if (elem := xml_elem.get(tag)) is not None:
                    return elem

                # Try to get value from attribute
                if (elem := xml_elem.find(tag)) is not None:
                    if "value" in elem.attrib:
                        return elem.attrib["value"]
                    elif elem.text and elem.text.strip():
                        return elem.text.strip()
                    return elem

                # Try findtext
                if (elem := xml_elem.findtext(tag)) is not None:
                    return elem.strip() if elem.strip() else None

                # Maybe it's a list?
                if elements := xml_elem.findall(tag):
                    return elements

        return None


_BGGBaseT = TypeVar("_BGGBaseT", bound=BGGBaseModel)


class BGGBaseList(SimpleListRoot[_BGGBaseT], Generic[_BGGBaseT], abc.ABC):
    """Base class for lists of BGG models."""

    @classmethod
    def base_cls(cls) -> _BGGBaseT:
        core_schema = cls.__pydantic_core_schema__
        schema = core_schema.get("schema")
        if schema is None:
            raise TypeError(f"Schema not found for {cls.__name__}")
        items_schema = schema.get("items_schema")
        if items_schema is None:
            raise TypeError(f"Items schema not found for {cls.__name__}")
        # HACK: need to do a better job handling the types that this could be
        assert not isinstance(items_schema, list), "Items schema should not be a list."
        base_cls = cast("_BGGBaseT | None", items_schema.get("cls"))
        if base_cls is None:
            raise TypeError(f"Base class not found for {cls.__name__}")
        return base_cls

    @model_validator(mode="before")
    @classmethod
    def validate_xml(cls, data: Any) -> Any:
        if isinstance(data, list):
            return [cls.base_cls().from_xml(item) for item in data]
        return data


class BGGLinkType(enum.StrEnum):
    """BGG link types."""

    CATEGORY = "boardgamecategory"
    MECHANIC = "boardgamemechanic"
    BOARD_GAME_DESIGNER = "boardgamedesigner"
    BOARD_GAME_PUBLISHER = "boardgamepublisher"
    BOARD_GAME_ARTIST = "boardgameartist"
    BOARD_GAME_FAMILY = "boardgamefamily"
    BOARD_GAME_EXPANSION = "boardgameexpansion"
    BOARD_GAME_ACCESSORY = "boardgameaccessory"
    BOARD_GAME_INTEGRATION = "boardgameintegration"
    BOARD_GAME_IMPLEMENTATION = "boardgameimplementation"


class BGGLink(BGGBaseModel):
    """BGG link element (categories, mechanics, etc.)."""

    link_type: Annotated[
        BGGLinkType, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="type")
    ]
    id: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
    value: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]


class BGGLinkList(BGGBaseList[BGGLink]):
    pass


class BGGName(BGGBaseModel):
    """BGG name element."""

    name_type: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="type")]
    value: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
    sort_index: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]


class BGGNameList(BGGBaseList[BGGName]):
    pass


class BGGPoll(BGGBaseModel):
    """BGG poll data."""

    name: str
    title: str
    total_votes: int
    results: dict[str, Any] = {}  # pyright: ignore[reportExplicitAny]


class BGGPollList(BGGBaseList[BGGPoll]):
    pass


class BGGStatistics(BGGBaseModel):
    """BGG statistics data."""

    page: int = 1

    users_rated: int | None = None
    average: float | None = None
    bayes_average: float | None = None
    stddev: float | None = None
    median: float | None = None

    owned: int | None = None
    trading: int | None = None
    wanting: int | None = None
    wishing: int | None = None

    num_comments: int | None = None
    num_weights: int | None = None
    average_weight: float | None = None

    ranks: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]


class BGGGame(BGGBaseModel):
    """BGG game data."""

    id: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
    game_type: Annotated[
        BGGGameType, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="type")
    ]

    names: Annotated[
        BGGNameList,
        XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="name", alias="name"),
    ] = BGGNameList.empty()

    # Basic info
    thumbnail: Annotated[HttpUrl | None, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)] = None
    image: Annotated[HttpUrl | None, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)] = None
    description: Annotated[str | None, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)] = None
    year_published: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="yearpublished")
    ] = None

    # Game mechanics
    min_players: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="minplayers")
    ] = None
    max_players: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="maxplayers")
    ] = None
    playing_time: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="playingtime")
    ] = None
    min_playtime: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="minplaytime")
    ] = None
    max_playtime: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="maxplaytime")
    ] = None
    min_age: Annotated[
        int | None, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="minage")
    ] = None

    links: Annotated[
        BGGLinkList, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="link")
    ] = BGGLinkList.empty()
    polls: BGGPollList = BGGPollList.empty()
    statistics: BGGStatistics | None = None

    fetched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    @property
    def primary_name(self) -> str:
        """Get the primary name of the game."""
        primary = next((n for n in self.names if n.name_type == "primary"), None)
        return primary.value if primary else str(self.id)

    @property
    def categories(self) -> BGGLinkList:
        """Get the categories of the game."""
        return self.links.filter(link_type=BGGLinkType.CATEGORY)

    @property
    def mechanics(self) -> BGGLinkList:
        """Get the mechanics of the game."""
        return self.links.filter(link_type=BGGLinkType.MECHANIC)

    @property
    def designers(self) -> BGGLinkList:
        """Get the designers of the game."""
        return self.links.filter(link_type=BGGLinkType.BOARD_GAME_DESIGNER)

    @property
    def publishers(self) -> BGGLinkList:
        """Get the publishers of the game."""
        return self.links.filter(link_type=BGGLinkType.BOARD_GAME_PUBLISHER)

    @property
    def bgg_rank(self) -> int | None:
        """Get the BGG rank of the game."""
        if not self.statistics or not self.statistics.ranks:
            return None

        for rank in self.statistics.ranks:
            if rank.get("type") == "boardgame":
                value = rank.get("value")
                if value and value != "Not Ranked":
                    # allow this to raise an error if the value cannot be converted to int
                    return int(value)  # pyright: ignore[reportAny]

        return None


class BGGGameList(BGGBaseList[BGGGame]):
    """List of BGG games."""


class BGGSearchResult(BGGBaseModel):
    """BGG search result item."""

    game_type: Annotated[BGGGameType, Field(alias="type")]
    id: int
    name: BGGName
    year_published: int | None = None


class BGGSearchResultList(BGGBaseList[BGGSearchResult]):
    pass


class BGGSearchResponse(BGGBaseModel):
    """BGG search response data."""

    total: int
    results: BGGSearchResultList = BGGSearchResultList.empty()


class BGGCollectionItem(BGGBaseModel):
    """BGG collection item."""

    object_type: str
    object_id: int
    sub_type: str
    call_id: int

    # Game info
    name: str
    year_published: int | None = None
    image: HttpUrl | None = None
    thumbnail: HttpUrl | None = None

    # Collection status
    own: bool = False
    prev_owned: bool = False
    for_trade: bool = False
    want: bool = False
    want_to_play: bool = False
    want_to_buy: bool = False
    wish_list: bool = False
    wish_list_priority: int | None = None

    # User data
    comment: str | None = None
    private_comment: str | None = None
    rating: float | None = None

    num_plays: int = 0


class BGGCollectionItemList(BGGBaseList[BGGCollectionItem]):
    """List of BGG collection items."""


class BGGCollection(BGGBaseModel):
    """BGG collection response."""

    items: BGGCollectionItemList = BGGCollectionItemList.empty()
    total_items: int = 0
    username: str | None = None

    fetched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))


if __name__ == "__main__":
    print(f"Flat case example: {flatcase('sort_index')}")

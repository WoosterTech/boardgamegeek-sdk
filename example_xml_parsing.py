#!/usr/bin/env python3
"""
Example demonstrating the new XML parsing system with lookup strategies.
"""

from typing import Annotated
from xml.etree import ElementTree as ET

from src.bgg.models.bgg import BGGBaseModel, XMLField, XMLLookupStrategy

# Example XML data
sample_xml = """
<game id="174430" type="boardgame">
    <name type="primary" sortindex="1" value="Gloomhaven"/>
    <name type="alternate" sortindex="1" value="Gloomhaven: Die düstere Stadt"/>
    <thumbnail>https://cf.geekdo-images.com/thumb/img/e7GyV4PiO5Z7ICtSNDGsmdXGBAM=/fit-in/200x150/pic2437871.jpg</thumbnail>
    <image>https://cf.geekdo-images.com/original/img/lDN1cHrOCj_vKu3zHlJEgHWyJec=/0x0/pic2437871.jpg</image>
    <description>Gloomhaven is a game of Euro-inspired tactical combat...</description>
    <yearpublished value="2017"/>
    <minplayers value="1"/>
    <maxplayers value="4"/>
    <playingtime value="120"/>
    <minplaytime value="60"/>
    <maxplaytime value="150"/>
    <minage value="14"/>
    <link type="boardgamecategory" id="1022" value="Adventure"/>
    <link type="boardgamecategory" id="1020" value="Exploration"/>
    <link type="boardgamemechanic" id="2023" value="Co-operative Play"/>
</game>
"""


class ExampleGame(BGGBaseModel):
    """Example game model demonstrating different XML lookup strategies."""

    # Attribute lookups - reads from XML attributes
    id: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
    game_type: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="type")]
    year_published: Annotated[
        int, XMLField(lookup_strategy=XMLLookupStrategy.FIND, xml_tag="yearpublished")
    ]

    # Text content lookups - reads text content of elements
    thumbnail: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]
    image: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]
    description: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]

    # FINDALL lookup - gets all matching elements (returns list)
    names: Annotated[list, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="name")]
    links: Annotated[list, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="link")]

    # AUTO lookup - lets the system decide the best strategy
    min_players: Annotated[
        int, XMLField(lookup_strategy=XMLLookupStrategy.AUTO, xml_tag="minplayers")
    ]
    max_players: Annotated[
        int, XMLField(lookup_strategy=XMLLookupStrategy.AUTO, xml_tag="maxplayers")
    ]


def main():
    """Demonstrate the XML parsing system."""

    # Parse the XML
    root = ET.fromstring(sample_xml)

    # Create the model from XML using the new system
    game = ExampleGame.from_xml(root)

    print("Parsed Game Data:")
    print(f"ID: {game.id}")
    print(f"Type: {game.game_type}")
    print(f"Year: {game.year_published}")
    print(f"Thumbnail: {game.thumbnail}")
    print(f"Names found: {len(game.names)}")
    print(f"Links found: {len(game.links)}")
    print(f"Min Players: {game.min_players}")
    print(f"Max Players: {game.max_players}")

    # Show how different strategies work
    print("\nDemonstrating different lookup strategies:")

    # Manual demonstrations
    print(f"ATTRIBUTE strategy for 'id': {root.get('id')}")
    print(f"TEXT strategy for 'thumbnail': {root.findtext('thumbnail')}")
    print(
        f"FIND strategy for 'yearpublished': {root.find('yearpublished').get('value') if root.find('yearpublished') is not None else None}"
    )
    print(f"FINDALL strategy for 'name': Found {len(root.findall('name'))} name elements")


if __name__ == "__main__":
    main()

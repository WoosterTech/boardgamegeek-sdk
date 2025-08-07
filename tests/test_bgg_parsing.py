from xml.etree import ElementTree as ET

from bgg.models.bgg import BGGGame, BGGGameType


def test_parse_wingspan_complete(wingspan_xml: str):
    root = ET.fromstring(wingspan_xml)

    item_elem = root.find("item")
    assert item_elem is not None, "Item element not found in XML"

    game = BGGGame.from_xml(item_elem)

    assert game.id == 266192
    assert game.game_type == BGGGameType.BOARD_GAME
    assert game.year_published == 2019
    assert len(game.names) == 18
    assert game.primary_name == "Wingspan"

    assert game.min_players == 1
    assert game.max_players == 5
    assert game.min_playtime == 40
    assert game.max_playtime == 70
    assert game.playing_time == 70
    assert game.min_age == 10

    assert game.categories.get(value="Animals") is not None

    # assert game.bgg_rank == 1  # source file does not provide rank

    assert game.description is not None
    assert "wingspan" in game.description.lower()


def test_unicode_characters():
    xml = """<?xml version="1.0" encoding="utf-8"?>
        <items>
            <item type="boardgame" id="123">
                <name type="primary" sortindex="1" value="Café International" />
                <description>A game with üñíçødé characters!</description>
                <link type="boardgamedesigner" id="1" value="François Désiré" />
            </item>
        </items>"""

    root = ET.fromstring(xml)
    item_elem = root.find("item")
    assert item_elem is not None, "Item element not found in XML"
    game = BGGGame.from_xml(item_elem)

    assert game.primary_name == "Café International"
    assert game.description is not None
    assert "üñíçødé" in game.description
    # assert game.designers is not None
    # assert "François Désiré" in game.designers.root


def test_realworld_gloomhaven(gloomhaven_xml: str):
    root = ET.fromstring(gloomhaven_xml)
    item_elem = root.find("item")
    assert item_elem is not None, "Item element not found in XML"

    game = BGGGame.from_xml(item_elem)

    assert game.year_published == 2017

    assert game.primary_name == "Gloomhaven"

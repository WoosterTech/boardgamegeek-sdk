import code
from pathlib import Path
from typing import Any, TypeVar
from xml.etree import ElementTree as ET

from pydantic import BaseModel, RootModel
from pydantic_core import CoreSchema
from rich import print as rprint

sample_data_path = Path("tests/sample_data")
assert sample_data_path.exists(), "Sample data path does not exist"


def load_sample_xml(filename: str) -> "ET.Element[str]":
    file_path = sample_data_path / filename
    assert file_path.exists(), f"Sample XML file {filename} does not exist"

    with file_path.open("rb") as f:
        data = f.read()

    rprint(f"[green]Loaded sample XML data from {file_path}[/green]")

    return ET.fromstring(data)


def main():
    gloomhaven_xml = load_sample_xml("gloomhaven.xml")

    code.interact(local=locals())


if __name__ == "__main__":
    # main()
    from typing import get_args

    from pydantic import RootModel

    _ModelT = TypeVar("_ModelT", bound=BaseModel)

    class MyBaseModel(BaseModel):
        value: str

    class MyModel(RootModel[list[MyBaseModel]]):
        pass

    class MyIntModel(RootModel[list[int]]):
        pass

    class MyDictModel(RootModel[dict[str, list[int]]]):
        pass

    class MyDictBaseModel(RootModel[dict[str, MyModel]]):
        pass

    def list_or_dict(schema: CoreSchema) -> bool:
        """Check if the schema is a list or dict type."""
        return schema.get("type") in ["list", "dict"]

    def get_root_type(model_cls: type[RootModel[_ModelT]]) -> CoreSchema | list[CoreSchema]:
        # First try generic metadata
        args = getattr(model_cls, "__pydantic_generic_metadata__", {}).get("args")
        if args:
            return args[0]

        # Fallback to core schema (less readable, but works)
        schema = model_cls.__pydantic_core_schema__["schema"]

        # rprint(f"[bold magenta]Core schema for {model_cls.__name__}: {schema}[/bold magenta]")

        if schema["type"] == "list":
            items_schema = schema.get("items_schema")
            if items_schema and "cls" in items_schema:
                return items_schema.get("cls")
            raise TypeError(
                f"Root type does not appear to be a pydantic model: {model_cls.__name__}"
            )

        if schema["type"] == "dict":
            items_schema = schema.get("items_schema")
            if items_schema and "cls" in items_schema:
                return items_schema.get("cls")
            raise TypeError(
                f"Root type does not appear to be a pydantic model: {model_cls.__name__}"
            )

    root_type = get_root_type(MyModel)
    rprint(f"[bold blue]Root type of MyModel: {root_type}[/]")

    try:
        int_root_type = get_root_type(MyIntModel)

        rprint(f"[bold blue]Root type of MyIntModel: {int_root_type['type']}[/]")
    except TypeError as e:
        rprint(f"[bold red]Error getting root type for MyIntModel: {e}[/bold red]")

    # dict_model_type = get_root_type(MyDictModel)
    # rprint(f"[bold blue]Root type of MyDictModel: {dict_model_type['type']}[/]")

    dict_base_model_type = get_root_type(MyDictBaseModel)
    rprint(f"[bold blue]Root type of MyDictBaseModel: {dict_base_model_type['type']}[/]")

    # code.interact(local=locals())

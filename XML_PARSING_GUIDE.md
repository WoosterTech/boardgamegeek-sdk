# XML Parsing System Documentation

## Overview

The new XML parsing system provides a flexible way to specify how fields should be extracted from XML elements using field annotations. This eliminates the need for hardcoded parsing logic and makes the models more declarative.

## XMLLookupStrategy Enum

The system supports five lookup strategies:

### 1. `XMLLookupStrategy.ATTRIBUTE`
Reads values from XML element attributes using `xml_elem.get(tag)`

**Usage:**
```python
id: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
```

**XML Example:**
```xml
<game id="174430" type="boardgame">
```
Would extract `id="174430"` and `type="boardgame"`

### 2. `XMLLookupStrategy.TEXT`
Reads text content from XML elements using `xml_elem.findtext(tag)`

**Usage:**
```python
description: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]
```

**XML Example:**
```xml
<description>This is a great game...</description>
```
Would extract the text content "This is a great game..."

### 3. `XMLLookupStrategy.FIND`
Finds the first matching child element using `xml_elem.find(tag)`, then extracts either the `value` attribute or text content

**Usage:**
```python
year_published: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.FIND, xml_tag="yearpublished")]
```

**XML Example:**
```xml
<yearpublished value="2017"/>
```
Would extract `value="2017"`

### 4. `XMLLookupStrategy.FINDALL`
Finds all matching child elements using `xml_elem.findall(tag)`, returns a list

**Usage:**
```python
names: Annotated[BGGNameList, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="name")]
```

**XML Example:**
```xml
<name type="primary" value="Gloomhaven"/>
<name type="alternate" value="Gloomhaven: Die düstere Stadt"/>
```
Would extract both name elements as a list

### 5. `XMLLookupStrategy.AUTO` (Default)
Let the system automatically determine the best lookup strategy based on the field name and XML structure. This provides backward compatibility and smart defaults.

## XMLField Function

The `XMLField` function creates a Pydantic Field with XML parsing metadata:

```python
def XMLField(
    *,
    lookup_strategy: XMLLookupStrategy = XMLLookupStrategy.AUTO,
    xml_tag: str | None = None,
    **kwargs: Any,
) -> Any:
```

**Parameters:**
- `lookup_strategy`: The XML lookup strategy to use
- `xml_tag`: Override the XML tag name (defaults to field name or alias)
- `**kwargs`: Any other Pydantic Field parameters

## Examples

### Basic Usage

```python
class BGGGame(BGGBaseModel):
    # Read from attributes
    id: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE)]
    game_type: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.ATTRIBUTE, alias="type")]
    
    # Read from text content
    thumbnail: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]
    description: Annotated[str, XMLField(lookup_strategy=XMLLookupStrategy.TEXT)]
    
    # Read from child elements with value attributes
    year_published: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.FIND, xml_tag="yearpublished")]
    
    # Read lists of child elements
    names: Annotated[BGGNameList, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="name")]
    
    # Let the system decide (backward compatible)
    min_players: Annotated[int, XMLField(lookup_strategy=XMLLookupStrategy.AUTO, xml_tag="minplayers")]
```

### XML Tag Override

Use `xml_tag` when the XML element name differs from your field name:

```python
year_published: Annotated[int, XMLField(
    lookup_strategy=XMLLookupStrategy.FIND, 
    xml_tag="yearpublished"  # XML uses "yearpublished" but field is "year_published"
)]
```

### Combining with Pydantic Field Parameters

You can still use all Pydantic Field parameters:

```python
rating: Annotated[float, XMLField(
    lookup_strategy=XMLLookupStrategy.ATTRIBUTE,
    description="Game rating from 1-10",
    ge=1.0,
    le=10.0
)]
```

## Migration from Old System

### Before (hardcoded logic):
```python
# In from_xml method
if tag == "name":
    value = xml_elem.findall("name")
    full_dict[tag] = value
elif tag == "links":
    value = xml_elem.findall("link")
    full_dict[tag] = value
```

### After (declarative):
```python
names: Annotated[BGGNameList, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="name")]
links: Annotated[BGGLinkList, XMLField(lookup_strategy=XMLLookupStrategy.FINDALL, xml_tag="link")]
```

## Benefits

1. **Declarative**: XML parsing logic is declared alongside the field definition
2. **Flexible**: Support for different XML patterns and structures
3. **Type-safe**: Leverages Python's type system
4. **Maintainable**: No more hardcoded parsing logic scattered throughout models
5. **Backward compatible**: AUTO strategy maintains existing behavior
6. **Extensible**: Easy to add new lookup strategies in the future

## Error Handling

The system will log warnings when fields cannot be found, but only when using explicit strategies (not AUTO). This helps with debugging while maintaining backward compatibility.

```python
logger.warning(f"Missing field '{tag}' in XML element {xml_elem.tag}")
```

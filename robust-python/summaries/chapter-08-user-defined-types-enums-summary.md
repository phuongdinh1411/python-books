# Chapter 8 – User-Defined Types: Enums

## Core Idea
**Enumerations** are the simplest user-defined type. They replace magic strings and integers with named, type-safe constants — making invalid values literally unrepresentable and code far more readable.

## Why User-Defined Types?
Using primitives (`str`, `int`, `tuple`) for domain concepts forces readers to constantly decode meaning:
```python
# Bad: what does restaurant[2] mean?
def calculate_tax(restaurant: tuple[str, str, str, int]) -> float:
    return subtotal * tax_lookup[restaurant[2]]

# Good: intention is clear
def calculate_tax(restaurant: Restaurant) -> Decimal:
    return subtotal * tax_lookup[restaurant.zip_code]
```
User-defined types tie code to **domain concepts** (Eric Evans, *Domain-Driven Design*).

## Enumerations

### Basic `Enum`
```python
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
```
- Each member is a named constant with a value
- Access: `Color.RED`, comparison: `Color.RED == Color.RED` → `True`
- Iteratable: `list(Color)` → all members

### When NOT to Use Enums
- When the set of values is dynamic or user-defined at runtime → use a `str` or a registry
- When members need associated behavior beyond a value → use a class or dataclass
- When you need numeric arithmetic on the values → use `IntEnum` (carefully) or a plain `int`

## Advanced Usage

### Automatic Values (`auto()`)
```python
from enum import Enum, auto

class Direction(Enum):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
```
- Values are assigned automatically (1, 2, 3, 4 by default)
- Removes the need to manage integer values manually; avoids off-by-one errors

### Flags
```python
from enum import Flag, auto

class Permission(Flag):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ALL = READ | WRITE | EXECUTE
```
- Supports bitwise operations: `Permission.READ | Permission.WRITE`
- Ideal for permission systems, feature flags, and bitmasks

### Integer Conversion (`IntEnum`)
```python
class Status(IntEnum):
    OK = 200
    NOT_FOUND = 404
```
- Members are also valid `int` values — interoperable with legacy integer APIs
- Use sparingly; prefer plain `Enum` when integer interop is not needed

### `@unique`
```python
from enum import Enum, unique

@unique
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 1  # ← raises ValueError at definition time
```
- Prevents accidental aliases where two members share the same value
- Explicit signal: every member is intentionally distinct

## Closing Thoughts
Enums are a lightweight but powerful tool. Replacing `"active"`, `"inactive"`, `"pending"` strings or `0`, `1`, `2` magic numbers with an `Enum` immediately makes code more readable, prevents typos, and gives the typechecker something concrete to check.

# Chapter 9 – User-Defined Types: Data Classes

## Core Idea
**Data classes** group related fields into a named, structured type. They replace raw dictionaries and tuples with something readable, type-safe, and auto-documented — without the boilerplate of writing a full class.

## Data Classes in Action
```python
from dataclasses import dataclass

@dataclass
class NutritionInfo:
    calories: int
    fat: float
    carbs: float
    protein: float
```
- The `@dataclass` decorator auto-generates `__init__`, `__repr__`, and `__eq__`
- Fields are declared with type annotations; default values are optional
- Clearer than `dict` or `tuple` for heterogeneous, named data

## Key Features

### String Conversion (`__repr__`)
Auto-generated: `NutritionInfo(calories=250, fat=9.0, carbs=30.0, protein=5.0)` — readable in logs and debuggers without manual work.

### Equality (`__eq__`)
Auto-generated field-by-field comparison:
```python
NutritionInfo(250, 9.0, 30.0, 5.0) == NutritionInfo(250, 9.0, 30.0, 5.0)  # True
```

### Relational Comparison (`order=True`)
```python
@dataclass(order=True)
class Version:
    major: int
    minor: int
    patch: int
```
Generates `__lt__`, `__le__`, `__gt__`, `__ge__` based on field order. Enables sorting.

### Immutability (`frozen=True`)
```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```
- Frozen dataclasses block ordinary field reassignment, but are **not deeply immutable**. Generated hashing works only when hash-participating fields are hashable; a frozen dataclass containing a list is not usable as a dict key.
- Raises `FrozenInstanceError` on attempted mutation
- Good for value objects (coordinates, money amounts, identifiers)

## Comparison to Other Types

### Data Classes vs. Dictionaries
| | Dict | Data Class |
|---|---|---|
| Key access | `d["name"]` (runtime error on typo) | `d.name` (typechecker catches typos) |
| Type safety | Available with `TypedDict` or precise annotations | Available through annotations; no automatic runtime validation |
| Readability | Low | High |
| Performance | Slightly faster | Negligible overhead |

### Data Classes vs. TypedDict
- `TypedDict` stays a real `dict` at runtime — required when you need `dict` compatibility (JSON, APIs)
- `dataclass` is a real class — preferred for internal domain models

### Data Classes vs. namedtuple
| | namedtuple | dataclass |
|---|---|---|
| Mutable | No | Yes (unless `frozen=True`) |
| Inheritance | Awkward | Natural |
| Default values | Verbose | Clean |
| Methods | Possible by subclassing or using `typing.NamedTuple` | Full class methods |

Use `namedtuple` only when you need tuple unpacking or tuple compatibility. Prefer `dataclass` otherwise.

## Closing Thoughts
Data classes hit the sweet spot between plain dictionaries (no structure, no safety) and full classes (too much boilerplate for pure data). They make domain models explicit, reduce bugs from dict key typos, and give the typechecker the information it needs to protect your code.

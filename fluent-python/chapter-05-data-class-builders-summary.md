# Chapter 5 – Data Class Builders

## Core Idea
Python offers three class builders — `collections.namedtuple`, `typing.NamedTuple`, and `@dataclass` — that eliminate the boilerplate of writing `__init__`, `__repr__`, and `__eq__` by hand. Choosing the right builder depends on whether you need immutability, type hints, or full class flexibility.

## Three Builders at a Glance

| Feature | `namedtuple` | `NamedTuple` | `@dataclass` |
|---|---|---|---|
| Base type | `tuple` subclass | `tuple` subclass | Plain class |
| Mutable | No | No | Yes (default); `frozen=True` for immutable |
| Type hints | No | Yes | Yes |
| Default values | Limited | Yes | Yes (`field(default=...)`) |
| Methods | Add later | Define in class body | Define in class body |
| `__slots__` | Built in | Built in | `@dataclass(slots=True)` (3.10+) |

## `collections.namedtuple`
```python
from collections import namedtuple
City = namedtuple('City', ['name', 'country', 'population'])
tokyo = City('Tokyo', 'JP', 36.933)
tokyo.name       # 'Tokyo'
tokyo._asdict()  # {'name': 'Tokyo', ...}
```

## `typing.NamedTuple`
```python
from typing import NamedTuple

class City(NamedTuple):
    name: str
    country: str
    population: float = 0.0   # default value

    def description(self) -> str:  # can add methods
        return f'{self.name}, {self.country}'
```

## `@dataclass`
```python
from dataclasses import dataclass, field

@dataclass
class City:
    name: str
    country: str
    population: float = 0.0
    tags: list[str] = field(default_factory=list)  # mutable default
```

### Important `field()` Options
- `default` — scalar default value
- `default_factory` — callable that produces a new default (use for lists, dicts)
- `init=False` — exclude from `__init__`; useful for computed attributes
- `repr=False` — exclude from `__repr__`
- `compare=False` — exclude from `__eq__` and ordering

### `@dataclass` Class Options
```python
@dataclass(frozen=True)   # immutable; enables hashing
@dataclass(order=True)    # generate __lt__, __le__, __gt__, __ge__
@dataclass(slots=True)    # use __slots__ for compact storage (3.10+)
@dataclass(eq=False)      # skip __eq__ generation
```

### Post-Init Processing
```python
@dataclass
class C:
    a: float
    b: float
    c: float = field(init=False)

    def __post_init__(self):
        self.c = self.a + self.b
```

## Type Hints 101
Annotations in class bodies are **purely descriptive at runtime**; Python does not enforce them automatically:
```python
class Foo:
    x: int = 'hello'   # valid Python — no error raised
```
Static checkers (mypy, pyright) read annotations and flag violations. Use `typing.ClassVar` to annotate class-level attributes that should not appear in `__init__`:
```python
from typing import ClassVar
@dataclass
class C:
    count: ClassVar[int] = 0  # class attribute, not a field
```

## Pattern Matching with Class Instances
Data class builders auto-generate `__match_args__`, enabling positional patterns:
```python
@dataclass
class Point:
    x: float
    y: float

match p:
    case Point(0, 0):
        print("origin")
    case Point(x, 0):
        print(f"on x-axis at {x}")
```

## Data Class as Code Smell
A class with only data and no behaviour (a "data class") may indicate **missing encapsulation**. Consider whether some of the code that manipulates the data belongs inside the class. Exceptions:
- **Scaffolding**: start with a data class while building early, add methods later
- **Intermediate representation**: DTO pattern for serialisation boundaries

## Closing Thoughts
`@dataclass` is the most flexible builder and the right default for new code. Use `NamedTuple` when immutability and tuple semantics (unpacking, CSV reading) matter. Avoid plain `namedtuple` in modern code — `NamedTuple` is strictly better with type hints. Whichever builder you choose, resist leaving the class as pure data; encapsulate invariants and behaviour where they belong.

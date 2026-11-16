# Chapter 8 – Type Hints in Functions

## Core Idea
Python's type hints enable **gradual typing**: a hybrid of traditional duck typing and the nominal typing used in Java/C++. You can adopt annotations incrementally and use tools like mypy to catch bugs statically without losing Python's dynamic flexibility.

## Gradual Typing
- Type hints have **no runtime effect** by default — Python remains dynamic
- A static checker (mypy, pyright) reads hints and flags type errors before execution
- `Any` is the escape hatch: consistent with every other type in both directions
- Code without annotations is treated as if everything is `Any`

```python
# Start untyped, add hints progressively
def double(x: float) -> float:
    return x * 2
```

## Starting with mypy
```bash
pip install mypy
mypy my_module.py
mypy --strict my_module.py   # full checks including missing annotations
```

mypy's `reveal_type(expr)` (a pseudo-function) prints the inferred type at analysis time.

## Types Are Defined by Supported Operations
Not all `float`-like objects are `float`. The right question is: what operations does this parameter need to support?
```python
def double(x: float) -> float: ...   # too narrow if any numeric works
def double(x: SupportsFloat) -> float: ...  # better; Protocol-based
```

## Key Types for Annotations

### Basics
```python
from typing import Optional, Union

def greet(name: str | None) -> str: ...       # Python 3.10+ union syntax
def greet(name: Optional[str]) -> str: ...    # equivalent, older style
def parse(data: int | str | bytes) -> int: ... # Union
```

### Collections
```python
from collections.abc import Sequence, Mapping, Iterable, Iterator, MutableSequence

def process(items: Sequence[int]) -> None: ...    # any sequence of ints
def lookup(table: Mapping[str, int]) -> None: ...
def stream(data: Iterable[float]) -> Iterator[float]: ...
```
Prefer abstract types (`Sequence`, `Mapping`, `Iterable`) in parameters; concrete types (`list`, `dict`) only where you need their specific interface.

### Generics with TypeVar
```python
from typing import TypeVar
T = TypeVar('T')

def first(items: Sequence[T]) -> T:   # T links input and output types
    return items[0]
```

### Tuple Types
```python
tuple[int, str]          # exactly (int, str)
tuple[int, ...]          # homogeneous tuple of any length
tuple[()]                # empty tuple
```

### Callable
```python
from collections.abc import Callable
Callable[[int, str], bool]    # (int, str) -> bool
Callable[..., bool]           # any args, returns bool
```

### Special Types
| Type | Meaning |
|---|---|
| `Any` | Compatible with every type (dynamic escape hatch) |
| `NoReturn` | Function never returns (raises, loops forever) |
| `Never` | A subtype of every type; a value that can never exist |
| `Optional[T]` | `T \| None` |
| `Union[A, B]` | `A \| B` |
| `Literal['r', 'w']` | Restricts to specific values |
| `Final` | Marks a constant that should not be reassigned |

## Static Protocols
Define structural interfaces for duck typing:
```python
from typing import Protocol

class SupportsClose(Protocol):
    def close(self) -> None: ...

def process(resource: SupportsClose) -> None:
    resource.close()
```
Any class with a matching `close()` method satisfies `SupportsClose` without inheritance.

## Annotating Special Parameters
```python
def f(*args: int, **kwargs: str) -> None: ...   # args: tuple[int,...]; kwargs: dict[str,str]

def g(a: int, b: int, /, c: int) -> int: ...    # a, b positional-only
```

## Imperfect Typing and Strong Testing
Type hints reduce but do not eliminate bugs. A well-typed program still needs tests:
- Static checkers catch type errors, not logical errors
- `Any` disables checking locally
- Runtime errors (e.g. wrong values, network failures) are outside the type system

The motto: **strong types AND strong tests**.

## Closing Thoughts
Gradual typing works best when adopted at boundaries first (function signatures, API surfaces) and enforced progressively via `--strict`. The key types to master are `Any`, `Optional`, `Union`, `Sequence`, `Mapping`, `TypeVar`, and `Protocol`. Types express what operations your code needs; they don't automatically validate external data at runtime — that requires Pydantic or similar.

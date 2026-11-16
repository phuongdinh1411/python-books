# Chapter 15 – More About Type Hints

## Core Idea
Python's type system goes beyond simple annotations: overloaded signatures, `TypedDict`, variance, generic classes, and `TypeVar` make it possible to express complex type relationships. These features require care because Python's type system is both gradual and structural.

## Overloaded Signatures
Use `@typing.overload` when a function can return different types based on its arguments:
```python
from typing import overload

@overload
def process(x: int) -> int: ...
@overload
def process(x: str) -> str: ...

def process(x):          # actual implementation (no decorator)
    if isinstance(x, int):
        return x * 2
    return x.upper()
```
Overloads are for static checkers only; only the un-decorated implementation runs.

## `TypedDict`
A dict with named keys and per-key type information:
```python
from typing import TypedDict

class Movie(TypedDict):
    title: str
    year: int
    rating: float
```
`TypedDict` is structural — any dict with the right keys satisfies it at the type-checker level. Unlike dataclasses, no class is created at runtime; it's just a `dict`.

## Type Casting
Tells the type checker to trust you about a type without runtime enforcement:
```python
from typing import cast

val = cast(int, some_expression)   # type checker believes val: int; no runtime effect
```
Use sparingly; it silences the checker without providing safety.

## Reading Type Hints at Runtime
```python
import typing
typing.get_type_hints(MyClass)   # returns resolved annotations dict
```
**Problem**: annotations are evaluated lazily (PEP 563, `from __future__ import annotations`), so `__annotations__` may contain strings, not actual types. Use `typing.get_type_hints()` to evaluate them properly.

## Generic Classes
```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()
```

### TypeVar Constraints vs Bounds
```python
T = TypeVar('T', int, str)     # T can only be int or str
T = TypeVar('T', bound=Number) # T must be Number or a subtype
```

## Variance

| Concept | Meaning | Example |
|---|---|---|
| **Covariant** | If `B` is a subtype of `A`, then `C[B]` is a subtype of `C[A]` | `Sequence[Dog]` ⊆ `Sequence[Animal]` (read-only containers) |
| **Contravariant** | If `B` is a subtype of `A`, then `C[A]` is a subtype of `C[B]` | `Callable[[Animal], None]` ⊆ `Callable[[Dog], None]` |
| **Invariant** | Neither direction | `list[Dog]` is not `list[Animal]` |

```python
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)
```

**Rule of thumb:**
1. Output type → covariant (data flows out)
2. Input type after construction → contravariant (data goes in)
3. Read-write → invariant

### Practical Examples
- `Sequence[T]` is covariant: you can only read from it
- `list[T]` is invariant: you can read AND write
- `Callable[[T], R]` is contravariant in T, covariant in R

## Generic Static Protocol
```python
from typing import Protocol, TypeVar
T_co = TypeVar('T_co', covariant=True)

class Readable(Protocol[T_co]):
    def read(self) -> T_co: ...
```

## Key PEPs Reference
| PEP | Feature | Python |
|---|---|---|
| 484 | Type Hints | 3.5 |
| 526 | Variable Annotations | 3.6 |
| 544 | Protocols (structural subtyping) | 3.8 |
| 589 | TypedDict | 3.8 |
| 585 | Generics in standard collections (`list[int]`) | 3.9 |
| 604 | `X \| Y` union syntax | 3.10 |
| 612 | `ParamSpec` | 3.10 |

## Closing Thoughts
Overloads and `TypedDict` solve everyday annotation problems. Variance is conceptually demanding but essential when designing reusable generic containers: read-only containers are covariant, read-write are invariant, and callbacks are contravariant. Use `typing.get_type_hints()` rather than `__annotations__` directly. The type system is still growing rapidly — follow Mypy's documentation for current best practices.

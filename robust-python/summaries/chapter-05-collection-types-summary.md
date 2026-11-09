# Chapter 5 – Collection Types

## Core Idea
Collections are everywhere in Python, but they're often annotated poorly — or not at all. Precise collection annotations communicate **what is stored, how homogeneous it is, and what operations are valid**.

## Annotating Collections
Basic collection annotations:
```python
list[str]          # list of strings
dict[str, int]     # string keys, int values
set[float]         # set of floats
tuple[int, str]    # exactly a 2-tuple of (int, str)
tuple[int, ...]    # variable-length tuple of ints
```
Without type parameters, `list` alone tells readers nothing about contents.

## Homogeneous vs. Heterogeneous Collections
- **Homogeneous**: all elements are the same type → use `list[T]`, `set[T]`, `dict[K, V]`
- **Heterogeneous**: elements have different, *meaningful* types → use `TypedDict`, `dataclass`, or `tuple[A, B, C]`
- Mixing heterogeneous data in a plain `list` or `dict[str, Any]` destroys type safety

## TypedDict
For dictionaries with a fixed, known schema:
```python
from typing import TypedDict

class Movie(TypedDict):
    title: str
    year: int
    rating: float
```
- Gives a named, documented structure to what would otherwise be an opaque `dict`
- Typechecker validates key names and value types
- Better than `dict[str, Any]` for structured data; similar to a dataclass but JSON-friendly

## Creating New Collections

### Generics
Define collections that work over any type with `Generic[T]`:
```python
from typing import Generic, TypeVar
T = TypeVar("T")

class Stack(Generic[T]):
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...
```
- Enables reusable, type-safe containers
- Callers get full type inference: `Stack[int]`, `Stack[str]`

### Modifying Existing Types
Subclass built-in collections (`UserList`, `UserDict`) to add custom behavior while keeping the full collection interface:
```python
from collections import UserList

class SortedList(UserList):
    def append(self, item): ...  # maintain sorted order
```
Prefer `UserList`/`UserDict` over subclassing `list`/`dict` directly to avoid subtle MRO issues.

### Abstract Base Classes (ABCs)
From `collections.abc`: `Sequence`, `MutableSequence`, `Mapping`, `MutableMapping`, `Iterable`, `Iterator`, etc.
- Accept ABCs in function signatures to be maximally flexible:
  ```python
  def process(items: Iterable[int]) -> None: ...
  ```
- Works with lists, generators, sets — anything iterable
- Annotate with the *least powerful* ABC that satisfies your needs (Liskov-friendly)

## Closing Thoughts
Collection types are where many bugs hide. Upgrading from bare `list` and `dict` to well-annotated, appropriately structured collection types makes data contracts explicit and lets the typechecker catch misuse before it becomes a production bug.

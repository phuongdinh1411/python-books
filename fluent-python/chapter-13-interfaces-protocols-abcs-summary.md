# Chapter 13 – Interfaces, Protocols, and ABCs

## Core Idea
Python supports **four approaches to typing**, each with different trade-offs. Choosing the right approach — duck typing, goose typing, static duck typing, or static typing — depends on how much you need runtime safety, static checking, and flexibility with third-party types.

## The Typing Map (Figure 13-1)

| Approach | How compatibility is determined | Checked at |
|---|---|---|
| **Duck typing** | Does the object have the right methods? (dynamic) | Runtime |
| **Goose typing** | Does the object inherit from an ABC or is it registered? | Runtime (`isinstance`) |
| **Static duck typing** | Does the object structurally match a `Protocol`? | Static analysis |
| **Static nominal typing** | Does the object's declared type match? | Static analysis |

## Duck Typing
Python goes to great lengths to make built-in protocols work with partial implementations:
- A class with only `__getitem__` is iterable and supports `in`
- A class with `__len__` + `__getitem__` is treated as a sequence
- Monkey-patching (adding methods at runtime) can make an object satisfy a protocol

```python
class Struggle:
    def __len__(self): return 23   # only this, yet for-loop, reversed, etc. all work

# Monkey-patch to satisfy the shuffle protocol:
FrenchDeck.__setitem__ = lambda self, pos, card: self._cards.__setitem__(pos, card)
random.shuffle(deck)   # now works
```

Defensive coding: use `try/except` rather than `hasattr`/`isinstance` (EAFP style).

## Goose Typing (ABCs)
Abstract Base Classes enforce explicit contracts:
```python
from collections.abc import MutableMapping

class MyMap(MutableMapping):
    def __getitem__(self, key): ...
    def __setitem__(self, key, val): ...
    def __delitem__(self, key): ...
    def __iter__(self): ...
    def __len__(self): ...
    # get, pop, update, etc. provided by MutableMapping mixin methods
```

### Standard ABCs in `collections.abc`

| ABC | Required methods |
|---|---|
| `Iterable` | `__iter__` |
| `Container` | `__contains__` |
| `Sized` | `__len__` |
| `Callable` | `__call__` |
| `Sequence` | `__getitem__`, `__len__` |
| `MutableSequence` | + `__setitem__`, `__delitem__`, `insert` |
| `Mapping` | `__getitem__`, `__len__`, `__iter__` |
| `MutableMapping` | + `__setitem__`, `__delitem__` |
| `Set` | `__contains__`, `__iter__`, `__len__` |

### Virtual Subclasses (Registration)
A class can satisfy an ABC without inheriting from it:
```python
@MyABC.register
class ThirdPartyClass: ...

isinstance(ThirdPartyClass(), MyABC)  # True
```
Or use `__subclasshook__` to define structural ABCs (like checking for a method name).

## Static Protocols (Python 3.8+)
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()
```
Any class with a `draw()` method satisfies `Drawable` — no inheritance needed. Static checkers verify the signature; `@runtime_checkable` enables shallow `isinstance` checks.

### Designing Good Protocols
- Keep protocols small — one or two methods
- Name them after the behaviour: `Sortable`, `Hashable`, `Closeable`
- Extend by composing: `class SortableHashable(Sortable, Hashable, Protocol): ...`
- Use `Protocol` for third-party/legacy types; use ABCs when you control all the types

### Extending Protocols
```python
class SizedIterable(Sized, Iterable, Protocol):
    pass   # composite protocol; no new methods required
```

## Numbers ABCs vs Numeric Protocols
| | `numbers.Number` hierarchy | `SupportsFloat`, `SupportsInt`, etc. |
|---|---|---|
| Runtime `isinstance` | ✅ Reliable | ⚠️ Issues with `complex` interplay |
| Static type checking | ❌ Not recommended | ✅ Works well |

Prefer `numbers` ABCs for runtime checks; numeric `Supports*` protocols for static checking.

## Closing Thoughts
Duck typing is Python's foundation; it is fluid and powerful but provides no static guarantees. Goose typing adds runtime contracts through ABCs, enabling `isinstance` checks and mixin methods. Static protocols bridge duck typing and static analysis. The right choice depends on context: use duck typing by default, ABCs when you want explicit runtime contracts on a class hierarchy you control, and protocols when writing typed library code.

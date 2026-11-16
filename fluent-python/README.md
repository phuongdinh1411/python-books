# Fluent Python (2nd Ed.) — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how do you write Python that uses the language fully, not just procedurally?

**Answer:** learn the data model — special methods are the API that integrates your objects with every Python feature. Then master sequences, mappings, functions-as-objects, class protocols, concurrency, and metaprogramming.

**Mental model:** every Python syntax feature (`for`, `with`, `+`, `[]`, `async for`) delegates to a special method. Implement the right methods and your objects become first-class citizens of the language.

The central theme is **idiomatic Python**: writing code that feels like it belongs in the standard library — readable, composable, and leveraging built-in machinery rather than fighting it.

## Quick Route (About 45–60 Minutes)

1. [Ch. 1: Data Model](chapter-01-python-data-model-summary.md) — understand the dunder protocol
2. [Ch. 2: Sequences](chapter-02-array-of-sequences-summary.md) — slicing, unpacking, sequence types
3. [Ch. 7: First-class functions](chapter-07-functions-as-first-class-objects-summary.md) — functions as values
4. [Ch. 9: Decorators](chapter-09-decorators-and-closures-summary.md) — closures and the decorator pattern
5. [Ch. 11: Pythonic objects](chapter-11-pythonic-object-summary.md) — build a complete class
6. [Ch. 13: Protocols and ABCs](chapter-13-interfaces-protocols-abcs-summary.md) — duck typing to static duck typing
7. [Ch. 17: Generators](chapter-17-iterators-generators-coroutines-summary.md) — iterators and generators
8. [Ch. 19: Concurrency](chapter-19-concurrency-models-summary.md) — threads vs processes vs coroutines

Then choose a deep-dive track based on your needs — see the chapter map below.

## Chapter Map

### Part I — Data Structures

| Chapter | What to retain |
|---|---|
| [1 — Python Data Model](chapter-01-python-data-model-summary.md) | Dunder methods are the API; every syntax feature delegates to them |
| [2 — Sequences](chapter-02-array-of-sequences-summary.md) | List vs tuple vs array; slicing; unpacking; augmented assignment gotchas |
| [3 — Dicts and Sets](chapter-03-dictionaries-and-sets-summary.md) | Hash tables; missing-key hooks; `defaultdict`; set operators on views |
| [4 — Unicode and Bytes](chapter-04-unicode-text-versus-bytes-summary.md) | Encode/decode at boundaries; normalise before comparing; Unicode sandwich |
| [5 — Data Class Builders](chapter-05-data-class-builders-summary.md) | `namedtuple` vs `NamedTuple` vs `@dataclass`; `field()`; `__post_init__` |
| [6 — Object References](chapter-06-object-references-mutability-summary.md) | Variables are labels; shallow vs deep copy; mutable defaults trap |

### Part II — Functions as Objects

| Chapter | What to retain |
|---|---|
| [7 — First-Class Functions](chapter-07-functions-as-first-class-objects-summary.md) | Nine callable types; `partial`; `operator` module; `inspect.signature` |
| [8 — Type Hints in Functions](chapter-08-type-hints-in-functions-summary.md) | Gradual typing; `Any`, `Optional`, `Union`, `TypeVar`, `Protocol` |
| [9 — Decorators and Closures](chapter-09-decorators-and-closures-summary.md) | Import-time vs call-time; `nonlocal`; `functools.cache`; `singledispatch` |
| [10 — Design Patterns](chapter-10-design-patterns-first-class-functions-summary.md) | Strategy and Command simplified by first-class functions |

### Part III — Classes and Protocols

| Chapter | What to retain |
|---|---|
| [11 — A Pythonic Object](chapter-11-pythonic-object-summary.md) | `__repr__`, `__hash__`, `__eq__`, `@property`, `__slots__` |
| [12 — Special Methods for Sequences](chapter-12-special-methods-sequences-summary.md) | `__getitem__`, `__len__`, slicing, `__getattr__`/`__setattr__` pairing |
| [13 — Interfaces, Protocols, ABCs](chapter-13-interfaces-protocols-abcs-summary.md) | Typing map; duck/goose/static-duck typing; Protocol design |
| [14 — Inheritance](chapter-14-inheritance-summary.md) | MRO; multiple inheritance; mixins; favour composition |
| [15 — More Type Hints](chapter-15-more-type-hints-summary.md) | Overloads; `TypedDict`; variance; generic classes |
| [16 — Operator Overloading](chapter-16-operator-overloading-summary.md) | Forward/reverse methods; return `NotImplemented`; rich comparisons |

### Part IV — Control Flow

| Chapter | What to retain |
|---|---|
| [17 — Iterators, Generators, Coroutines](chapter-17-iterators-generators-coroutines-summary.md) | Generator functions; `yield from`; `itertools`; classic coroutines |
| [18 — with, match, else](chapter-18-with-match-else-summary.md) | Context managers; `@contextmanager`; pattern matching; `for/else` |
| [19 — Concurrency Models](chapter-19-concurrency-models-summary.md) | GIL; threads vs processes vs coroutines; when each applies |
| [20 — Concurrent Executors](chapter-20-concurrent-executors-summary.md) | `ThreadPoolExecutor`; `ProcessPoolExecutor`; `Future`; `as_completed` |
| [21 — Asynchronous Programming](chapter-21-asynchronous-programming-summary.md) | `async/await`; tasks; semaphores; blocking calls; `run_in_executor` |

### Part V — Metaprogramming

| Chapter | What to retain |
|---|---|
| [22 — Dynamic Attributes and Properties](chapter-22-dynamic-attributes-properties-summary.md) | `__getattr__` vs `__getattribute__`; property factories; `cached_property` |
| [23 — Attribute Descriptors](chapter-23-attribute-descriptors-summary.md) | Overriding vs non-overriding; methods as descriptors; `__set_name__` |
| [24 — Class Metaprogramming](chapter-24-class-metaprogramming-summary.md) | `type()`; `__init_subclass__`; class decorators; metaclasses |

## Do Not Confuse

- **`__str__` vs `__repr__`**: `__repr__` is for developers (unambiguous, ideally eval-able); `__str__` is for users. If only one is defined, `__repr__` is the fallback.
- **`__getattr__` vs `__getattribute__`**: `__getattr__` fires only on misses; `__getattribute__` fires on every access — overriding it risks infinite recursion.
- **Overriding vs non-overriding descriptor**: a data descriptor (`__get__` + `__set__`) takes precedence over instance `__dict__`; a non-overriding descriptor (`__get__` only) can be shadowed by an instance attribute.
- **Iterator vs iterable**: an iterable produces an iterator via `__iter__`; an iterator has `__next__` and remembers its position. Never make them the same object.
- **`is` vs `==`**: `is` checks identity (same object in memory); `==` checks value equality. Use `is` only for singletons (`None`, `True`, `False`).
- **Thread vs process for CPU-bound work**: threads do NOT bypass the GIL; only `ProcessPoolExecutor` or C extensions that release the GIL give true CPU parallelism.
- **`await` ≠ parallel**: `await` yields control cooperatively; it is not multi-threaded. A blocking call inside an `async` function freezes the event loop.
- **Covariant vs invariant collections**: `list[Dog]` is NOT a subtype of `list[Animal]`; `Sequence[Dog]` IS (read-only view, covariant).

## Practice (30–40 Minutes)

Implement a `Measured` descriptor that validates a numeric value is within a range, then build a `Sensor` dataclass using it:

```python
from dataclasses import dataclass

class Measured:
    def __set_name__(self, owner, name):
        self.name = name
        self._name = '_' + name

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi

    def __get__(self, obj, objtype=None):
        if obj is None: return self
        return getattr(obj, self._name, None)

    def __set__(self, obj, value):
        if not (self.lo <= value <= self.hi):
            raise ValueError(f'{self.name} must be in [{self.lo}, {self.hi}]')
        setattr(obj, self._name, value)

@dataclass
class Sensor:
    temperature: float = 0.0
    humidity: float = 0.0

# Replace plain float fields with Measured descriptors
Sensor.temperature = Measured(-40, 85)
Sensor.humidity = Measured(0, 100)
```

Extend to: make `Sensor` iterable (yields `(name, value)` pairs), hashable, and printable with `__repr__`. Add a generator that reads from a stream and yields `Sensor` objects.

## Self-Check

1. What is the difference between a classmethod alternative constructor and a regular `__new__` override? When would you choose each?
2. Why does subclassing `dict` directly sometimes fail to trigger your overridden `__setitem__`? What should you do instead?
3. Explain the "all-or-nothing" problem with async functions. Why can't you call `await` inside a regular function?
4. A `TypeVar` is declared `covariant=True`. What does that mean for a `Container[T]`? Can you append to a `Container[int]` if it is typed as `Container[float]`?
5. What is the MRO for `class D(B, C)` where both `B` and `C` inherit from `A`? In what order are methods resolved?

**Answer cues:** `classmethod` for alternate construction requiring class reference; `__new__` for controlling the type of the returned object; subclass `UserDict` instead; all callers in the async chain must be `async def`; covariant means `Container[int] :> Container[float]` (subtypes allowed as sources); MRO is D→B→C→A→object.

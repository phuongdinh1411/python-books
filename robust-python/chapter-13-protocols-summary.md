# Chapter 13 – Protocols

## Core Idea
**Protocols** bridge the gap between Python's runtime duck typing and the static typechecker. They let you annotate duck-typed behavior without forcing inheritance hierarchies — giving you the best of both worlds.

## The Tension Between Typing Systems
Python supports duck typing: any object supporting the right methods can be used in any context. But typecheckers work statically and don't know at analysis time whether an object will have the right methods.

**The problem**: you want to write a function that accepts "anything splittable" — but without a shared base class, the typechecker has no way to verify it.

### Naive Solutions and Their Problems

| Approach | Problem |
|---|---|
| Type blank / `Any` | Loses all type safety |
| `Union[BLT, Wrap, Soup]` | Must update the Union every time a new type is added |
| Inheritance | Forces all "splittable" things to share a base class — not always natural or possible |
| Mixins | Similar coupling problem; fragile with multiple inheritance |

## Protocols (Python 3.8+)
```python
from typing import Protocol, Self  # Self requires Python 3.11+; use typing_extensions on older versions

class Splittable(Protocol):
    def split_in_half(self) -> tuple[Self, Self]: ...
```
- Any class that implements `split_in_half` **implicitly** satisfies `Splittable` — no inheritance needed
- This is **structural subtyping**: compatibility is based on structure (methods/attributes), not declaration
- The typechecker can verify that a passed object has the right shape

```python
def split_dish(dish: Splittable) -> tuple[Splittable, Splittable]:
    return dish.split_in_half()
```
Now the typechecker verifies that `dish` has `split_in_half` — without forcing every dish class to inherit from anything.

## Advanced Usage

### Composite Protocols
```python
class Serializable(Protocol):
    def to_json(self) -> str: ...

class Cacheable(Serializable, Protocol):
    def cache_key(self) -> str: ...
```
Compose protocols to define richer structural requirements.

### Runtime Checkable Protocols
```python
from typing import runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> None: ...

isinstance(obj, Drawable)  # works at runtime
```
- By default, `isinstance()` with a Protocol raises `TypeError`
- `@runtime_checkable` enables `isinstance` checks — useful for runtime dispatch
- Warning: only checks that methods *exist*, not their signatures

### Modules Satisfying Protocols
A module can satisfy a Protocol if it has the right top-level functions/attributes:
```python
import my_module
def process(handler: Loggable) -> None: ...
process(my_module)  # valid if my_module has the required attributes
```
Useful for plugin systems where the "plugin" is a module.

## Protocols vs. ABCs
| | Protocol | ABC |
|---|---|---|
| Coupling | Structural; no shared base required | Usually nominal inheritance; some ABCs also support registration or structural runtime checks |
| Third-party types | Can satisfy without modification | Runtime registration may work, but does not add methods or establish static inheritance |
| Runtime checks | Opt-in `@runtime_checkable`, presence checks only | `isinstance` recognizes inheritance/registration; abstract methods block incomplete subclass instantiation |
| Typechecker support | ✅ Full | ✅ Full |

Use **ABCs** when you own all the types and want explicit contract enforcement.  
Use **Protocols** when you want flexibility, especially with third-party or legacy types.

## Closing Thoughts
Protocols are one of the most powerful additions to Python's type system. They allow you to express duck-typed relationships statically without coupling types via inheritance. The result is flexible, composable code that still benefits from typechecker verification.

# Chapter 19 – Pluggable Python

## Core Idea
**Pluggable code** defines a framework with **extension points** — slots where future developers snap in new behavior without modifying the core. Like a stand mixer with interchangeable attachments: the mixer is stable, the attachments are swappable.

## The Goal
You can't predict all future needs. Instead of trying to be prescient, build a solid foundation with well-defined extension points. Future collaborators extend via new plugins — not edits to existing code.

## Pattern 1: Template Method Pattern
Define a skeleton algorithm in a base class; let subclasses fill in the variable steps:
```python
from abc import ABC, abstractmethod

class MealPreparer(ABC):
    def prepare(self) -> None:       # the template method
        self.gather_ingredients()
        self.cook()
        self.plate()

    def gather_ingredients(self) -> None: ...  # default or abstract

    @abstractmethod
    def cook(self) -> None: ...      # subclass fills this in

    def plate(self) -> None: ...     # default behavior
```
- The invariant steps live in the base class
- The variable steps are `@abstractmethod` — subclasses provide specializations
- Adding a new meal type = new subclass, no changes to `MealPreparer`

**Use when**: the algorithm structure is fixed but specific steps vary by type.

## Pattern 2: Strategy Pattern
Inject behavior as an object/function rather than inheriting it:
```python
class KitchenAssistant:
    def __init__(self, cooking_strategy: CookingStrategy):
        self._strategy = cooking_strategy

    def prepare_meal(self, ingredients: list[str]) -> Meal:
        return self._strategy.cook(ingredients)
```
- Behavior is a **dependency** — passed in, not inherited
- Swap strategies at runtime or via configuration
- Cleaner than Template Method when the strategy is truly independent

**Use when**: the varying behavior is completely independent of the object using it; or when you need runtime behavior swapping.

## Template Method vs. Strategy

| | Template Method | Strategy |
|---|---|---|
| Variation mechanism | Inheritance | Composition |
| Coupling | Tight (IS-A) | Loose (HAS-A) |
| Runtime swap | No | Yes |
| Best for | Fixed algorithm, variable steps | Completely interchangeable behaviors |

## Plug-in Architectures
For maximum extensibility — third parties or users provide plugins at deploy time, not at compile time:

### Discovery Mechanisms
1. **Entry points** (via `setuptools`/`importlib.metadata`):
   ```python
   from importlib.metadata import entry_points
   plugins = entry_points(group="my_app.plugins")
   ```
   Third-party packages declare themselves as plugins in their `pyproject.toml`.

2. **Explicit registration**:
   ```python
   PLUGIN_REGISTRY: dict[str, type] = {}

   def register_plugin(name: str):
       def decorator(cls):
           PLUGIN_REGISTRY[name] = cls
           return cls
       return decorator

   @register_plugin("grilled_cheese")
   class GrilledCheeseMaker: ...
   ```

3. **Directory scanning**: dynamically import all `.py` files in a plugins directory.

### Design Principles for Plug-in Systems
- Define a clear, minimal protocol/interface that all plugins must satisfy
- Validate plugins at load time (not at use time)
- Fail loudly if a plugin is malformed
- Keep the plugin interface stable — it's a public API

## Closing Thoughts
Pluggable design is the culmination of extensibility, composability, and dependency management. It's what separates a system that you maintain alone from one that a community can build upon. Define the right extension points, keep the interface minimal, and let the future write itself.

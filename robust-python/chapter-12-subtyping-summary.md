# Chapter 12 – Subtyping

## Core Idea
Subtyping creates relationships *between* types. When applied correctly it allows new behaviors to be added without breaking existing code. When applied incorrectly it creates fragile hierarchies that erode robustness. The guiding principle is the **Liskov Substitution Principle (LSP)**.

## Inheritance
A child class inherits all attributes and methods of a parent class:
```python
class Animal:
    def speak(self) -> str: ...

class Dog(Animal):
    def speak(self) -> str:
        return "Woof"
```
- Child "is-a" parent — `Dog` IS-AN `Animal`
- Inherits behavior; can override and extend
- Tempting to overuse — not every "similar thing" relationship warrants inheritance

## Substitutability (Liskov Substitution Principle)
> If `S` is a subtype of `T`, then objects of type `T` may be replaced with objects of type `S` without altering any of the desirable properties of the program.

In practice: **any subclass must be usable wherever the parent is expected, without surprises.**

### LSP Violations to Avoid
- Strengthening preconditions (requiring more from callers than the parent did)
- Weakening postconditions (returning less/different than the parent guaranteed)
- Raising new exceptions the parent never raised
- Overriding a method so it does something completely different

### The Classic Violation: Square extends Rectangle
```python
class Rectangle:
    def set_width(self, w): self._width = w
    def set_height(self, h): self._height = h

class Square(Rectangle):  # WRONG: violates LSP
    def set_width(self, w):
        self._width = w
        self._height = w  # surprise side effect!
```
A `Square` cannot substitute for a `Rectangle` without surprising callers. Despite the geometric is-a relationship, the behavioral contract is broken.

## Design Considerations

### When to Use Inheritance
- When the subtype truly IS-A supertype **in terms of behavior**, not just structure
- When you want polymorphism: callers treat different subtypes uniformly
- Keep hierarchies shallow — deep hierarchies are hard to reason about

### Composition Over Inheritance
Prefer building complex types from simpler ones:
```python
class Engine:
    def start(self): ...

class Car:
    def __init__(self):
        self._engine = Engine()  # HAS-AN Engine

    def start(self):
        self._engine.start()
```
- "HAS-A" relationship instead of "IS-A"
- More flexible: swap `Engine` implementation without changing `Car`
- Avoids the fragile base class problem
- Easier to reason about in isolation

### Abstract Base Classes
Use `ABC` and `@abstractmethod` to define a contract without a complete implementation:
```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...
```
- Subtypes *must* implement abstract methods
- Enables polymorphism with typechecker support

## Closing Thoughts
Subtyping is powerful but dangerous when misapplied. Always ask: "Can this subtype fully substitute for the parent without surprising callers?" If not, use composition instead. The LSP is not just a guideline — it's the difference between a type hierarchy that helps and one that creates subtle, hard-to-find bugs.

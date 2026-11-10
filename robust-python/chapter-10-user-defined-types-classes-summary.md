# Chapter 10 – User-Defined Types: Classes

## Core Idea
Classes group state and behavior and can protect **invariants** — rules about data that must always hold for valid objects. A dataclass is also a full Python class: it can define methods, properties, and validation such as `__post_init__`. Choose an ordinary class when explicit state transitions and controlled initialization matter more than generated field-based behavior.

## Class Anatomy
A class groups data (attributes) and behavior (methods). Unlike a data class, a full class is used when:
- Internal state needs protection from external mutation
- Complex initialization logic is required
- Invariants must be maintained across operations

### Constructors
`__init__` is where invariants are first established:
```python
class BoundedList:
    def __init__(self, max_size: int):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._items: list = []
```
Validate inputs in `__init__` to prevent invalid objects from ever existing.

## Invariants
An invariant is a condition that is **always true** for a valid object:
- A `BankAccount` balance is never negative
- A `Date` always has a valid month (1–12)
- A `BoundedList` never exceeds its max size

### Why Invariants Are Beneficial
- If an invariant holds, every method can assume it without re-checking
- Bugs become impossible, not just unlikely
- Code that consumes the class is simpler (no defensive null checks everywhere)

### Avoiding Broken Invariants
- Establish invariants in `__init__`; raise exceptions for violations
- Never expose mutable internal state directly
- All mutation paths (every method that changes state) must re-validate the invariant

### Communicating Invariants
- Document them in the class docstring
- Use type annotations where possible
- Use property decorators with validation setters

## Encapsulation

### Protecting Data Access
Use name mangling and properties to control access:
```python
class Temperature:
    def __init__(self, celsius: float):
        self.celsius = celsius  # use the setter so construction validates too

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Below absolute zero")
        self._celsius = value
```
- `_name` convention = "don't touch unless you know what you're doing"
- `__name` = name-mangled, harder to access accidentally
- Properties enforce validation on every write

### Operations
Methods should express domain operations, not raw field mutations:
```python
# Bad: exposes internals
account._balance += 100

# Good: operation enforces invariants
account.deposit(100)
```
Operations are the vocabulary of your domain. Well-named methods communicate intent; raw field access does not.

## When NOT to Use Classes
- Pure data with no behavior → use `dataclass`
- Stateless utility functions → use module-level functions
- Classes with only one method → consider a function instead
- Classes with no `self` usage in methods → those should be free functions

## Closing Thoughts
Classes are about protecting invariants and expressing domain operations. Don't default to classes for everything — use the simplest structure that meets your needs. When you do use a class, take encapsulation seriously: never let callers put your object into an invalid state.

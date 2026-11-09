# Chapter 6 – Classes and Objects: Beyond the Basics

## Core Idea
Python's object system goes far beyond simple classes and methods. Properties, factory patterns, the Observer pattern, and magic methods unlock powerful design patterns — and even allow you to build domain-specific languages on top of regular Python syntax.

## Key Concepts

### Properties
Properties let you expose attributes with controlled read/write access, without changing the calling code.

**Read-only property:**
```python
class Coupon:
    def __init__(self, amount):
        self._amount = amount
    @property
    def amount(self):
        return self._amount
```

**Validated setter:**
```python
class Ticket:
    def __init__(self, price):
        self.price = price  # Uses the setter — validates on init too!
    @property
    def price(self):
        return self._price
    @price.setter
    def price(self, new_price):
        if new_price < 0:
            raise ValueError("Nice try")
        self._price = new_price
```

**Refactoring shield:** Change internal representation (e.g., `total_cents`) while keeping the public API (`dollars`, `cents`) working — callers never know the difference.

---

### Factory Patterns

#### Simple Factory — Alternate Constructors with `@classmethod`
```python
class Money:
    def __init__(self, dollars, cents): ...

    @classmethod
    def from_pennies(cls, total_cents):
        return cls(total_cents // 100, total_cents % 100)

    @classmethod
    def from_string(cls, amount):
        # parse "$140.75"...
        return cls(dollars, cents)
```
- `cls` = the class itself (not `self`)
- Works correctly with **subclasses** — `TipMoney.from_pennies(475)` returns a `TipMoney`
- Make `__init__` the most generic constructor; `@classmethod` methods are alternate entry points

#### Factory Method — Dynamic Type Selection
```python
READERS = {
    'gif': GIFReader,
    'jpg': JPEGReader,
    'png': PNGReader,
}

def get_image_reader(path):
    reader_class = READERS.get(extension_of(path), RawByteReader)
    return reader_class(path)
```
- Stores class objects in a dict; picks the right one at runtime
- More readable and maintainable than a chain of `if/elif`

---

### The Observer Pattern (pub-sub)
- **Publisher**: detects events, notifies subscribers
- **Subscriber**: registers a callback to be called when an event occurs

**Pythonic version** — use callable objects (method references), not just a required `update()` method:
```python
class Publisher:
    def __init__(self):
        self.subscribers = dict()

    def register(self, who, callback=None):
        if callback is None:
            callback = who.update
        self.subscribers[who] = callback

    def dispatch(self, message):
        for callback in self.subscribers.values():
            callback(message)
```
- `callback` can be any callable — a method, a function, or an object with `__call__`
- **Multiple channels**: use a dict of dicts `{channel: {subscriber: callback}}`

---

### Magic Methods
Override these to make your objects work with Python's operators and built-ins.

**Arithmetic:**
| Method | Operation |
|---|---|
| `__add__` | `a + b` |
| `__sub__` | `a - b` |
| `__mul__` | `a * b` |
| `__truediv__` | `a / b` |
| `__mod__` | `a % b` |

**Representation:**
- `__str__()` — used by `print()`, f-strings, `str()`; human-readable
- `__repr__()` — used by `repr()` and `!r`; ideally reproducible Python code

**Equality and comparison:**
- `__eq__()` — `==` (default is identity check; almost always override this)
- `__lt__`, `__le__`, `__gt__`, `__ge__` — rich comparisons; Python can infer one from the other

---

### Rebelliously Misusing Magic Methods
Magic methods don't have to behave as their names imply. **Pandas DataFrames** exploit this:
```python
positive_rows = df[df.A > 0]
```
- `df.A > 0` calls `__gt__()`, which returns a **Series** (a vector of booleans), not a plain `bool`
- `df[...]` calls `__getitem__()`, which uses that Series to filter rows

This technique lets you implement **lazy expression trees** and **domain-specific languages** on top of Python syntax — the user writes natural-looking code without realizing the operators are doing custom work.

## Key Takeaways
- Use `@property` to enforce invariants, make attributes read-only, or refactor internal state without breaking external code
- `@classmethod` with `cls` is the Pythonic way to implement alternate constructors
- The Factory Method pattern maps strings/types → classes using a dict, not `if/elif` chains
- The Observer pattern is more flexible in Python when callbacks are method objects (not just `update()`)
- Magic methods let instances work with Python operators; they don't have to return the "expected" types — enabling powerful library design

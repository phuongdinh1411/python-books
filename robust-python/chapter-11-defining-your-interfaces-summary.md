# Chapter 11 – Defining Your Interfaces

## Core Idea
> **The Paradox of Code Interfaces**: You have one chance to get your interface right, but you won't know it's right until it's used.

Designing great interfaces requires thinking like a user *before* they exist. Python provides powerful tools — magic methods and context managers — to make types feel natural and idiomatic.

## Natural Interface Design

### Thinking Like a User
- Imagine yourself as a developer who has never seen your code; what would you expect?
- The **Law of Least Surprise**: the interface should do exactly what it looks like it does
- Test your design by writing calling code before implementing: if the call site looks awkward, the interface is wrong
- Good interfaces make the right thing easy and the wrong thing hard

### The Cost of Getting It Wrong
Once code is in production and dependents exist, changing an interface is expensive. The cost of a backward-incompatible change is proportional to the number of callers. Design deliberately up front.

## Natural Interactions

### Natural Interfaces in Action
Design methods to match idiomatic Python patterns users already know:
```python
# Instead of: cookbook.get_recipes_list()
# Use iteration protocol:
for recipe in cookbook:
    print(recipe)
```
Follow Python conventions so your types feel like first-class citizens.

### Magic Methods (Dunder Methods)
Magic methods let your objects participate in Python's built-in syntax:

| Method | Enables |
|---|---|
| `__len__` | `len(obj)` |
| `__getitem__` | `obj[key]`, `for x in obj` |
| `__contains__` | `x in obj` |
| `__add__` | `obj + other` |
| `__eq__` | `obj == other` |
| `__repr__` | `repr(obj)`, debugger display |
| `__str__` | `str(obj)`, `print(obj)` |
| `__bool__` | `if obj:` truthiness |
| `__iter__` / `__next__` | full iteration protocol |

Implement the magic methods that make **semantic sense** for your type — don't implement `__add__` on a `User` just because you can.

### Context Managers (`__enter__` / `__exit__`)
```python
class DatabaseConnection:
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False  # don't suppress exceptions
```
Used with `with` statements:
```python
with DatabaseConnection() as db:
    db.query(...)
```
- Guarantees cleanup even when exceptions occur
- Communicates a **scoped resource** pattern idiomatically
- Use `contextlib.contextmanager` for a simpler decorator-based approach

## Closing Thoughts
Interface design is the highest-leverage design decision you make. Once published, it's nearly impossible to change without breaking callers. Invest in thinking like a user, leverage Python's magic methods to make your types feel natural, and use context managers to express resource ownership clearly.

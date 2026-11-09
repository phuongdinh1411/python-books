# Chapter 4 – Decorators

## Core Idea
A **decorator** is a function that wraps another function, adding behavior before and/or after it runs — without modifying the original function's code. Decorators enable powerful metaprogramming patterns and are widely used in popular Python libraries (Flask, Django, pytest, etc.).

## Key Concepts

### How Decorators Work
`@some_decorator` before a `def` is shorthand for:
```python
def foo(x): ...
foo = some_decorator(foo)
```
- The **decorator** takes the bare function as argument and returns a new **decorated function**
- The **bare function** is the original definition; the **decorated function** is what gets called

### The Basic Decorator Pattern
```python
def printlog(func):
    def wrapper(*args, **kwargs):
        print("CALLING: " + func.__name__)
        return func(*args, **kwargs)
    return wrapper

@printlog
def foo(x):
    print(x + 2)
```
- Use `*args, **kwargs` in `wrapper` to make the decorator compatible with **any function signature**
- The prototypical form is the one to memorize

### Data in Decorators — Scope Matters
- Variables defined **inside the decorator** (but outside `wrapper`) are created **once per decorated function**
- Variables defined **inside `wrapper`** are reset on every call — wrong for accumulators
- Variables defined **outside the decorator** are shared by all decorated functions — also wrong
```python
def running_average(func):
    data = {"total": 0, "count": 0}  # ✅ correct scope
    def wrapper(*args, **kwargs):
        val = func(*args, **kwargs)
        data["total"] += val
        data["count"] += 1
        ...
    return wrapper
```

### Exposing Decorator State
Attach decorator data as an attribute on the wrapper object:
```python
wrapper.data = data
return wrapper
# Later: foo.data  → {'total': 7, 'count': 2}
```

### `nonlocal` for Mutable Scalars
Mutating a dictionary in the enclosing scope works without `nonlocal` (you're calling a method, not reassigning the variable). But reassigning a scalar requires `nonlocal`:
```python
def countcalls(func):
    count = 0
    def wrapper(*args, **kwargs):
        nonlocal count
        count += 1
        ...
    return wrapper
```

### Decorators That Take Arguments
A decorator with arguments is a **function that returns a decorator**:
```python
def add(increment):
    def decorator(func):
        def wrapper(n):
            return func(n) + increment
        return wrapper
    return decorator

@add(2)
def foo(x): return x ** 2
# Equivalent to: foo = add(2)(foo)
```

### Class-Based Decorators
Implement via `__call__()`:
```python
class PrintLog:
    def __init__(self, func):
        self.func = func
    def __call__(self, *args, **kwargs):
        print(f"CALLING: {self.func.__name__}")
        return self.func(*args, **kwargs)
```
Advantages over function-based:
- Can use **inheritance** to share code between related decorators
- State lives naturally in `self` attributes (no `nonlocal` needed)
- For argument-taking class decorators: `__init__` receives the arguments, `__call__` receives the function

### Decorators for Classes
Decorators can also be applied to classes (not just functions):
```python
def autorepr(cls):
    def cls_repr(self):
        return f"{cls.__name__}()"
    cls.__repr__ = cls_repr
    return cls  # Return the same class, modified

@autorepr
class Penny:
    value = 1
```
- Prefer modifying and returning the **original class** over creating a subclass (keeps type identity clean)

## Key Takeaways
- A decorator is just a function that takes a function and returns a function
- Use `wrapper(*args, **kwargs)` to make decorators work with any signature
- Variable scope inside the decorator controls whether state is per-decorated-function or shared
- Use `nonlocal` when reassigning a scalar in the enclosing scope
- Class-based decorators are better when you need inheritance or prefer object-oriented state management
- Decorators can also be applied to classes to add/modify class-level behavior

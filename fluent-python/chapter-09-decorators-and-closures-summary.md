# Chapter 9 – Decorators and Closures

## Core Idea
Decorators are callable objects that replace a function with another function (or class). Understanding how they work requires understanding **when Python executes decorators**, **variable scoping**, and **closures** — concepts that are also the foundation of callbacks and functional-style programming.

## Decorators 101
```python
@decorate
def func():
    ...
# Equivalent to:
func = decorate(func)
```
A decorator is applied at **import time**, not when the function is called. The decorator runs once, and the result is bound to the original name.

## Import Time vs Runtime
- **Import time**: the module body executes, function bodies are compiled, decorators are applied
- **Runtime**: when a function is actually called

```python
registry = []

def register(func):    # registration decorator — side effect only
    registry.append(func)
    return func        # returns function unchanged

@register
def f1(): pass
@register
def f2(): pass

# After import: registry == [f1, f2]
```

## Variable Scope Rules (LEGB)
Python resolves names in: **L**ocal → **E**nclosing → **G**lobal → **B**uilt-in

```python
b = 6
def f(a):
    print(a)
    print(b)   # reads global b
    b = 9      # MAKES b local to f — now print(b) above raises UnboundLocalError!
```
The `global` declaration makes a name always refer to the module-level variable. `nonlocal` refers to the nearest enclosing scope's variable.

## Closures
A closure is a function that retains bindings from an **enclosing scope** that has already finished executing:
```python
def make_averager():
    series = []

    def averager(new_value):
        series.append(new_value)   # series is a free variable
        return sum(series) / len(series)

    return averager

avg = make_averager()
avg(10)  # 10.0
avg(11)  # 10.5
avg(12)  # 11.0
```

## `nonlocal`
Required when you need to **rebind** (not just mutate) a free variable:
```python
def make_averager():
    count = 0
    total = 0.0

    def averager(new_value):
        nonlocal count, total   # rebind, not just read
        count += 1
        total += new_value
        return total / count

    return averager
```

## Implementing a Simple Decorator
```python
import functools, time

def clock(func):
    @functools.wraps(func)        # preserves __name__, __doc__, etc.
    def clocked(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        print(f'{func.__name__}({args}) → {result!r} [{elapsed:.8f}s]')
        return result
    return clocked
```

## Standard Library Decorators
### `functools.cache` / `functools.lru_cache`
```python
@functools.cache                    # unbounded memoisation (3.9+)
def fibonacci(n):
    return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)

@functools.lru_cache(maxsize=128)   # bounded LRU cache
def expensive(x): ...
```

### `functools.singledispatch`
Overload a function based on the **type of the first argument**:
```python
from functools import singledispatch

@singledispatch
def process(obj):
    raise NotImplementedError

@process.register(int)
def _(obj):
    return f'integer {obj}'

@process.register(str)
def _(obj):
    return f'string {obj}'
```

## Parameterised Decorators
A decorator with parameters requires three levels of nesting:
```python
def clock(fmt='[{elapsed:.8f}s] {name}({args}) → {result}'):
    def decorate(func):
        @functools.wraps(func)
        def clocked(*_args):
            t0 = time.perf_counter()
            _result = func(*_args)
            elapsed = time.perf_counter() - t0
            name = func.__name__
            args = ', '.join(repr(a) for a in _args)
            print(fmt.format(**locals()))
            return _result
        return clocked
    return decorate

@clock(fmt='{name}: {elapsed:.2f}s')
def my_func(): ...
```

Alternatively, implement a class with `__init__` (stores parameters) and `__call__` (wraps the function).

## Closing Thoughts
Decorators are concise only because closures exist. The pattern `outer (config) → decorator (func) → wrapper (*args)` appears everywhere in Python frameworks. `functools.wraps` is mandatory in production decorators — without it, debugging becomes hard. Mastering closures and `nonlocal` also unlocks async callbacks, event handlers, and the Strategy pattern.

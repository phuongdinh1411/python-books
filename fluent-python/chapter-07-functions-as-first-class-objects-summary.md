# Chapter 7 – Functions as First-Class Objects

## Core Idea
Functions in Python are **first-class objects**: they can be assigned to variables, stored in data structures, passed as arguments, and returned from other functions. This enables functional programming patterns and powerful higher-order abstractions.

## Functions Are Objects
```python
def factorial(n):
    return 1 if n < 2 else n * factorial(n - 1)

fact = factorial       # assign to variable
fact(5)                # 120
map(factorial, range(6))  # pass as argument
```
Every function has a `__doc__`, `__name__`, `__module__`, `__code__`, `__annotations__`, `__defaults__`, and `__kwdefaults__` attribute.

## Higher-Order Functions
A function that takes a function as argument or returns one. Classic examples: `map`, `filter`, `sorted`.

Modern Pythonic alternatives:
```python
# map + filter → list comprehension or generator expression
list(map(factorial, range(5)))         # traditional
[factorial(n) for n in range(5)]       # Pythonic

list(filter(lambda n: n % 2, range(5)))  # odds
[n for n in range(5) if n % 2]          # clearer

# reduce → sum, any, all, max, min
from functools import reduce
from operator import add
reduce(add, range(5))   # 10; same as sum(range(5))
```

## Anonymous Functions (lambda)
```python
sorted(fruits, key=lambda word: word[::-1])  # sort by reversed spelling
```
Limited to a single expression. For anything complex, use a named function.

## Nine Flavours of Callable
| Kind | Example |
|---|---|
| User-defined function | `def f()` |
| Built-in function | `len`, `open` |
| Built-in method | `dict.get` |
| Instance method | `obj.method` |
| Class | `MyClass()` calls `__new__` then `__init__` |
| Class method | `@classmethod` |
| Static method | `@staticmethod` |
| Generator function | `def f(): yield ...` |
| Callable instance | class with `__call__` |

Test with `callable(obj)`.

## User-Defined Callable Types
Any object with `__call__` behaves like a function:
```python
class BingoCage:
    def __init__(self, items):
        self._items = list(items)
        random.shuffle(self._items)

    def __call__(self):
        return self._items.pop()
```

## Keyword-Only and Positional-Only Parameters
```python
def f(a, b, *, c):    # c is keyword-only (after *)
    ...

def f(a, b, /, c):    # a and b are positional-only (before /)
    ...
```

## `operator` Module
Replaces lambdas with reusable callables:
```python
from operator import mul, itemgetter, methodcaller

sorted(data, key=itemgetter('name'))
sorted(data, key=attrgetter('country', 'city'))

upcase = methodcaller('upper')
upcase('hello')   # 'HELLO'

triple = partial(mul, 3)  # see below
```

## `functools.partial`
Freeze some arguments of a function to create a new callable with fewer parameters:
```python
from functools import partial
from operator import mul

triple = partial(mul, 3)
triple(7)   # 21
list(map(triple, range(10)))
```
Also useful to adapt a function to an API requiring a specific signature.

## Inspecting Functions
```python
import inspect
sig = inspect.signature(factorial)
str(sig)            # '(n)'
for name, param in sig.parameters.items():
    print(param.kind, name, param.default)
```
`inspect.Parameter.kind` values: `POSITIONAL_ONLY`, `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL`, `KEYWORD_ONLY`, `VAR_KEYWORD`.

## Closing Thoughts
First-class functions are the foundation of Python's functional capabilities. `map`/`filter`/`reduce` are usually replaced by comprehensions or built-ins, but `operator.itemgetter`, `functools.partial`, and callable objects fill important gaps. Understanding function attributes and `inspect.signature` matters when writing frameworks or decorators.

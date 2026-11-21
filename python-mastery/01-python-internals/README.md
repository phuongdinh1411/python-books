# Pillar 1 — Python Internals

> **Duration:** 2 weeks | **Priority:** 🔴 Critical

---

## 🎯 Learning Objectives

By the end of this pillar you will be able to:
- Explain how CPython manages memory (reference counting + GC)
- Read and interpret Python bytecode using `dis`
- Explain the GIL and its impact on concurrency
- Write custom descriptors, metaclasses, and `__dunder__` methods
- Understand how Python's import system works under the hood
- Use `__slots__` to reduce memory footprint

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [Python Data Model — Official Docs](https://docs.python.org/3/reference/datamodel.html) | 📄 Docs | ✅ Free |
| [Inside the Python Virtual Machine — Obi Ike-Nwosu](https://leanpub.com/insidethepythonvirtualmachine/read) | 📄 eBook | ✅ Free |
| [CPython Developer Guide — Internals](https://devguide.python.org/internals/) | 📄 Docs | ✅ Free |
| [Python `dis` module docs](https://docs.python.org/3/library/dis.html) | 📄 Docs | ✅ Free |
| [Python Descriptors — Real Python](https://realpython.com/python-descriptors/) | 📄 Article | ✅ Free |
| [Python Metaclasses — Real Python](https://realpython.com/python-metaclasses/) | 📄 Article | ✅ Free |
| [Raymond Hettinger — Super considered super! (YouTube)](https://www.youtube.com/watch?v=EiOglTERPEo) | 🎥 Video | ✅ Free |
| [Brandon Rhodes — All About Dicts (YouTube)](https://www.youtube.com/watch?v=66P5FMkWoVU) | 🎥 Video | ✅ Free |

> 💡 **Optional paid books** (excellent supplements if available via library/trial):
> *Fluent Python 2nd Ed* (Luciano Ramalho), *CPython Internals* (Real Python)

---

## Section 1 — The CPython Object Model

### Every Python Object is a C struct

In CPython, every Python object (int, str, list, your class) is represented internally
as a C struct called `PyObject`. It contains at minimum:

- `ob_refcnt` — the reference count
- `ob_type` — a pointer to the type (class)

```python
import sys

x = [1, 2, 3]
print(sys.getrefcount(x))   # usually 2 (x + the getrefcount arg)

y = x
print(sys.getrefcount(x))   # 3 now

del y
print(sys.getrefcount(x))   # back to 2
```

### Reference Counting

Python tracks how many variables point to an object.
When the count hits 0, the memory is freed immediately.

```python
import sys

a = "hello"
print(sys.getrefcount(a))   # varies; small strings may be interned

b = a
print(sys.getrefcount(a))   # +1

del b
print(sys.getrefcount(a))   # back to previous
```

**Why this matters:** Reference counting is fast but cannot handle **circular references**.

### Circular Reference Problem

```python
import gc

class Node:
    def __init__(self, val):
        self.val = val
        self.next = None

a = Node(1)
b = Node(2)
a.next = b
b.next = a   # circular!

del a, b
# ref count never hits 0!
# Python's cyclic GC handles this
gc.collect()  # force a GC cycle
```

### The Garbage Collector

CPython has a **generational GC** on top of reference counting, specifically to handle cycles.

```python
import gc

print(gc.get_threshold())   # (700, 10, 10) — generation thresholds
print(gc.get_count())       # (n0, n1, n2) — objects in each generation

gc.disable()   # you can disable it (dangerous; only if no cycles)
gc.enable()

# Find cycles:
gc.set_debug(gc.DEBUG_LEAK)
gc.collect()
```

**Generations:**
- Gen 0: new objects; collected most often
- Gen 1: survived one Gen 0 collection
- Gen 2: long-lived objects (rarely collected)

### Object Identity and Interning

```python
# Small integers (-5 to 256) are interned — same object in memory
a = 100
b = 100
print(a is b)   # True — same object!

a = 1000
b = 1000
print(a is b)   # False — different objects

# Short strings may also be interned
s1 = "hello"
s2 = "hello"
print(s1 is s2)   # True (implementation detail)

# Force string interning
import sys
s1 = sys.intern("a very long string that won't be interned automatically")
s2 = sys.intern("a very long string that won't be interned automatically")
print(s1 is s2)   # True
```

**Rule:** Always use `==` for value comparison; use `is` only for `None`, `True`, `False`.

---

## Section 2 — The GIL (Global Interpreter Lock)

### What Is It?

The GIL is a mutex (lock) inside CPython that ensures **only one thread executes Python
bytecode at a time**, even on multi-core machines.

It exists to protect CPython's reference counting from race conditions.

```
Thread 1: runs bytecode   ──────────────────────
Thread 2: waits for GIL   ───────────────────────
                  (every ~15ms, GIL is released and re-acquired)
```

### Impact on Concurrency

```python
import threading
import time

COUNT = 50_000_000

def countdown(n):
    while n > 0:
        n -= 1

# Single-threaded
start = time.perf_counter()
countdown(COUNT)
end = time.perf_counter()
print(f"Single: {end - start:.2f}s")

# Two threads (same core due to GIL!)
t1 = threading.Thread(target=countdown, args=(COUNT // 2,))
t2 = threading.Thread(target=countdown, args=(COUNT // 2,))
start = time.perf_counter()
t1.start(); t2.start()
t1.join(); t2.join()
end = time.perf_counter()
print(f"Two threads: {end - start:.2f}s")  # Often SLOWER due to GIL contention!
```

### The GIL IS Released For:
- I/O operations (network, disk)
- C extension calls that explicitly release it (NumPy, etc.)
- `time.sleep()`

```python
# I/O-bound: threads work well despite GIL
import threading
import urllib.request

def fetch(url):
    urllib.request.urlopen(url)

# These truly run in parallel because GIL is released during I/O
threads = [threading.Thread(target=fetch, args=("http://example.com",)) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
```

### Workarounds
- **I/O-bound:** use `threading` or `asyncio` — GIL released during I/O
- **CPU-bound:** use `multiprocessing` — each process has its own GIL
- **CPython 3.13+:** experimental free-threaded mode (`--disable-gil`)

---

## Section 3 — Python Bytecode & the `dis` Module

### How Python Executes Code

```
Source (.py)  →  Tokenizer  →  AST  →  Compiler  →  Bytecode (.pyc)  →  CPython VM
```

### Reading Bytecode

```python
import dis

def add(a, b):
    return a + b

dis.dis(add)
# Output:
#   2           0 LOAD_FAST                0 (a)
#               2 LOAD_FAST                1 (b)
#               4 BINARY_OP               0 (+)
#               8 RETURN_VALUE
```

### Comparing Implementations

```python
import dis

def list_comp():
    return [x * 2 for x in range(10)]

def for_loop():
    result = []
    for x in range(10):
        result.append(x * 2)
    return result

print("--- List comprehension ---")
dis.dis(list_comp)
print("\n--- For loop ---")
dis.dis(for_loop)
# List comp uses BUILD_LIST + optimized bytecode
```

### Inspecting Code Objects

```python
def greet(name: str) -> str:
    greeting = f"Hello, {name}!"
    return greeting

code = greet.__code__
print(code.co_varnames)    # ('name', 'greeting')
print(code.co_consts)      # (None, 'Hello, ', '!')
print(code.co_argcount)    # 1
print(code.co_filename)    # file path
```

---

## Section 4 — The Python Data Model (`__dunder__` Methods)

The Python data model lets you hook your objects into Python's built-in syntax.

### `__repr__` and `__str__`

```python
class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        # For developers: should be unambiguous
        return f"Point({self.x!r}, {self.y!r})"

    def __str__(self) -> str:
        # For end users: readable
        return f"({self.x}, {self.y})"

p = Point(1.0, 2.0)
print(repr(p))   # Point(1.0, 2.0)
print(str(p))    # (1.0, 2.0)
print(p)         # (1.0, 2.0) — calls __str__
```

### Arithmetic Operators

```python
class Vector:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Vector":
        return Vector(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector":
        # Handles: 3 * v (when int.__mul__ returns NotImplemented)
        return self.__mul__(scalar)

    def __abs__(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __bool__(self) -> bool:
        return bool(abs(self))

    def __repr__(self) -> str:
        return f"Vector({self.x}, {self.y})"

v1 = Vector(1, 2)
v2 = Vector(3, 4)
print(v1 + v2)    # Vector(4, 6)
print(v1 * 3)     # Vector(3, 6)
print(3 * v1)     # Vector(3, 6) — uses __rmul__
print(abs(v2))    # 5.0
```

### Container Protocol

```python
class BoundedList:
    """A list that enforces a max size."""
    def __init__(self, max_size: int):
        self._data: list = []
        self._max = max_size

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def __contains__(self, item) -> bool:
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def append(self, item):
        if len(self._data) >= self._max:
            raise OverflowError(f"Max size {self._max} reached")
        self._data.append(item)

bl = BoundedList(3)
bl.append(1); bl.append(2); bl.append(3)
print(len(bl))       # 3
print(2 in bl)       # True
for item in bl:      # iteration works
    print(item)
```

### Context Manager Protocol

```python
class ManagedFile:
    def __init__(self, path: str, mode: str = "r"):
        self.path = path
        self.mode = mode
        self._file = None

    def __enter__(self):
        self._file = open(self.path, self.mode)
        return self._file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()
        # Return False to propagate exceptions, True to suppress
        return False

with ManagedFile("/tmp/test.txt", "w") as f:
    f.write("hello")
```

---

## Section 5 — Descriptors

Descriptors are the mechanism behind `property`, `classmethod`, `staticmethod`.
They let you define custom attribute access logic.

### The Descriptor Protocol

A descriptor is any object that defines `__get__`, `__set__`, or `__delete__`.

```python
class Validator:
    """A descriptor that validates values on assignment."""
    def __set_name__(self, owner, name):
        # Called when the class is defined
        self.name = name
        self.storage_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self  # accessed on the class, not instance
        return getattr(instance, self.storage_name, None)

    def __set__(self, instance, value):
        value = self.validate(value)
        setattr(instance, self.storage_name, value)

    def validate(self, value):
        return value


class PositiveNumber(Validator):
    def validate(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self.name} must be a number")
        if value <= 0:
            raise ValueError(f"{self.name} must be positive")
        return value


class Circle:
    radius = PositiveNumber()
    
    def __init__(self, radius: float):
        self.radius = radius  # triggers __set__

    @property
    def area(self) -> float:
        import math
        return math.pi * self.radius ** 2


c = Circle(5.0)
print(c.area)       # 78.53...
c.radius = -1       # raises ValueError
```

### `property` Is a Descriptor

```python
class Temperature:
    def __init__(self, celsius: float = 0.0):
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float):
        if value < -273.15:
            raise ValueError("Temperature below absolute zero!")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9/5 + 32

t = Temperature(25)
print(t.fahrenheit)   # 77.0
t.celsius = -300      # raises ValueError
```

---

## Section 6 — `__slots__`

By default, every Python object stores its attributes in a `__dict__` (a dictionary).
`__slots__` replaces this with fixed-size C arrays — faster and uses less memory.

```python
import sys

class WithDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y

a = WithDict(1, 2)
b = WithSlots(1, 2)

print(sys.getsizeof(a.__dict__))   # ~232 bytes for the dict
# b has no __dict__!

# Memory comparison (using many objects)
import tracemalloc
tracemalloc.start()
items_dict = [WithDict(i, i) for i in range(100_000)]
print(tracemalloc.get_traced_memory())   # current, peak
tracemalloc.reset_peak()
items_slots = [WithSlots(i, i) for i in range(100_000)]
print(tracemalloc.get_traced_memory())   # noticeably smaller
tracemalloc.stop()
```

**Use `__slots__` when:** you create millions of instances (data records, nodes, points).
**Don't use** when you need dynamic attributes or inheritance flexibility.

---

## Section 7 — Metaclasses

A metaclass is the class of a class. `type` is the default metaclass.

```python
# type() can create classes dynamically
MyClass = type("MyClass", (object,), {"x": 10, "greet": lambda self: f"Hello from {self.x}"})
obj = MyClass()
print(obj.greet())   # Hello from 10


# Custom metaclass
class SingletonMeta(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Database(metaclass=SingletonMeta):
    def __init__(self):
        self.connection = "connected"


db1 = Database()
db2 = Database()
print(db1 is db2)   # True — same instance


# Registry metaclass — auto-register subclasses
class PluginMeta(type):
    registry: dict = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        PluginMeta.registry[cls.__name__] = cls


class BasePlugin(metaclass=PluginMeta):
    pass

class CSVPlugin(BasePlugin):
    pass

class JSONPlugin(BasePlugin):
    pass

print(PluginMeta.registry)
# {'CSVPlugin': <class 'CSVPlugin'>, 'JSONPlugin': <class 'JSONPlugin'>}
```

---

## Section 8 — The Import System

### How `import` Works

```
import foo
  1. Check sys.modules (cache) — return if found
  2. Find the module (sys.meta_path finders)
  3. Load the module (execute its code)
  4. Add to sys.modules
  5. Bind the name in the local namespace
```

```python
import sys

# See all loaded modules
print(list(sys.modules.keys())[:10])

# sys.path — where Python looks for modules
print(sys.path)

# Reload a module (useful during development)
import importlib
import mymodule
importlib.reload(mymodule)
```

### Package `__init__.py`

```python
# package/
# ├── __init__.py
# ├── utils.py
# └── models.py

# __init__.py controls what 'from package import *' exports
# and can expose sub-module contents at package level

# package/__init__.py
from .utils import helper_fn
from .models import User

__all__ = ["helper_fn", "User"]
```

### Lazy Imports (for performance)

```python
# Heavy imports can slow startup; defer them
def process_image(path: str):
    from PIL import Image   # only imported when function is called
    img = Image.open(path)
    return img
```

---

## Section 9 — `weakref` — Avoid Memory Leaks in Caches

Strong references keep objects alive. `weakref` lets you reference an object without
preventing garbage collection — perfect for caches and observers.

```python
import weakref
import gc

class HeavyObject:
    def __init__(self, name: str):
        self.name = name
        print(f"Created {name}")

    def __del__(self):
        print(f"Destroyed {self.name}")

# Strong reference — keeps obj alive
obj = HeavyObject("A")
strong = obj
del obj
gc.collect()
print(strong.name)  # still alive because strong holds it

# Weak reference — doesn't keep obj alive
obj = HeavyObject("B")
weak = weakref.ref(obj)
print(weak())       # <HeavyObject>
del obj
gc.collect()
print(weak())       # None — object was collected!

# WeakValueDictionary — cache that doesn't prevent GC
cache: weakref.WeakValueDictionary[str, HeavyObject] = weakref.WeakValueDictionary()

obj_a = HeavyObject("cached_A")
cache["a"] = obj_a

print("a" in cache)   # True
del obj_a
gc.collect()
print("a" in cache)   # False — entry auto-removed!

# Real use case: observer/callback pattern without memory leaks
class EventBus:
    def __init__(self):
        self._listeners: list[weakref.ref] = []

    def subscribe(self, callback) -> None:
        self._listeners.append(weakref.ref(callback))

    def emit(self, event: str) -> None:
        # Clean up dead references and call live ones
        alive = []
        for ref in self._listeners:
            cb = ref()
            if cb is not None:
                cb(event)
                alive.append(ref)
        self._listeners = alive
```

---

## Section 10 — `__init_subclass__` — The Clean Alternative to Metaclasses

`__init_subclass__` is called when a class is subclassed. It's simpler than a metaclass
for most plugin/registry use cases.

```python
class Plugin:
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, name: str | None = None, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        key = name or cls.__name__.lower().replace("plugin", "")
        Plugin._registry[key] = cls
        print(f"Registered plugin: {key!r}")

class CSVPlugin(Plugin, name="csv"):
    def process(self, data: str) -> list:
        return data.split(",")

class JSONPlugin(Plugin, name="json"):
    def process(self, data: str) -> dict:
        import json
        return json.loads(data)

# Auto-registered on class definition:
print(Plugin._registry)
# {'csv': <class CSVPlugin>, 'json': <class JSONPlugin>}

plugin = Plugin._registry["csv"]()
print(plugin.process("a,b,c"))   # ['a', 'b', 'c']

# Validate subclasses on creation
class Validator:
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        required = ["validate", "serialize"]
        for method in required:
            if not hasattr(cls, method):
                raise TypeError(f"{cls.__name__} must implement {method}()")

class GoodValidator(Validator):
    def validate(self, x): return True
    def serialize(self, x): return str(x)

# class BadValidator(Validator):  # raises TypeError immediately!
#     pass
```

---

## Section 11 — Python 3.13 Free-Threaded Mode (No GIL)

Python 3.13 introduced experimental free-threaded builds (PEP 703).

```python
# Check if running free-threaded
import sys
print(sys._is_gil_enabled())   # False in free-threaded build

# Install free-threaded Python:
# uv python install 3.13t   (the 't' suffix = free-threaded)
# python3.13t -c "import sys; print(sys._is_gil_enabled())"

# In free-threaded mode, CPU-bound threads CAN run in parallel:
import threading
import time

def cpu_work(n: int) -> int:
    return sum(i * i for i in range(n))

# With free-threaded Python, these run on separate cores simultaneously
threads = [threading.Thread(target=cpu_work, args=(5_000_000,)) for _ in range(4)]
start = time.perf_counter()
for t in threads: t.start()
for t in threads: t.join()
print(f"Free-threaded: {time.perf_counter() - start:.2f}s")
# ~4x faster than GIL-locked CPython for CPU-bound work!

# CAUTION: free-threaded Python requires thread-safe code
# - dict is NOT thread-safe in free-threaded mode
# - Use threading.Lock() for shared mutable state
# - Most C extensions need updates to work correctly
# Production status as of 2024: experimental, not production-ready

# Practical status:
# - Python 3.12: GIL (default), no free-threaded option
# - Python 3.13: GIL (default) + experimental free-threaded build (opt-in)
# - Python 3.14+: working toward stable free-threaded support
```

---

## 🏋️ Exercises

### Exercise 1 — Custom `cached_property`

Implement a `@cached_property` descriptor that:
- Computes the value on first access
- Caches it in the instance
- Is thread-safe

```python
import threading

class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.lock = threading.Lock()

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        val = instance.__dict__.get(self.attrname, _NOT_SET := object())
        if val is _NOT_SET:
            with self.lock:
                # Double-checked locking
                val = instance.__dict__.get(self.attrname, _NOT_SET)
                if val is _NOT_SET:
                    val = self.func(instance)
                    instance.__dict__[self.attrname] = val
        return val

# Test it
class Circle:
    def __init__(self, radius):
        self.radius = radius

    @cached_property
    def area(self):
        import math
        print("Computing area...")
        return math.pi * self.radius ** 2

c = Circle(5)
print(c.area)   # "Computing area..." then the value
print(c.area)   # just the value — no recomputation
```

### Exercise 2 — Bytecode Investigation

```python
# Compare these implementations with dis.dis():
# 1. String concatenation: "a" + "b" + "c" vs f"{'a'}{'b'}{'c'}"
# 2. Dict creation: dict(a=1) vs {"a": 1}
# 3. Conditional: x if cond else y vs (cond and x) or y

import dis

# Your analysis here:
def concat_plus(a, b, c):
    return a + b + c

def concat_fstring(a, b, c):
    return f"{a}{b}{c}"

dis.dis(concat_plus)
print("---")
dis.dis(concat_fstring)
```

### Exercise 3 — Memory Profiling with `__slots__`

Create 1,000,000 instances with and without `__slots__` and measure the memory difference.

---

## ✅ Self-Check Questions

1. What is `ob_refcnt` and when does CPython free memory?
2. Why can't reference counting alone handle circular references?
3. What is the GIL and what problem does it solve?
4. For what types of work does the GIL get released?
5. What does `dis.dis(func)` show you?
6. What is a descriptor? Name three built-in descriptors.
7. When would you use `__slots__`?
8. What does a metaclass control?
9. What is the order Python follows when resolving an `import`?
10. Why should `__repr__` return a string that could recreate the object?

---

## 📖 Reading Checklist

- [ ] Fluent Python Ch 1 — The Python Data Model
- [ ] Fluent Python Ch 6 — Object References, Mutability, Recycling
- [ ] Fluent Python Ch 22 — Dynamic Attributes and Properties
- [ ] Fluent Python Ch 23 — Attribute Descriptors
- [ ] Fluent Python Ch 24 — Class Metaprogramming
- [ ] Python Data Model — Official Docs (fully)
- [ ] CPython Internals — Ch 1–4

---

## 🔗 Key Links

- https://docs.python.org/3/reference/datamodel.html
- https://docs.python.org/3/library/dis.html
- https://docs.python.org/3/library/gc.html
- https://realpython.com/python-descriptors/
- https://realpython.com/python-metaclasses/

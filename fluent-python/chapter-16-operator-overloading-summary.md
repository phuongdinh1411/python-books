# Chapter 16 – Operator Overloading

## Core Idea
Python allows user-defined classes to support infix operators (`+`, `*`, `@`, `==`, etc.) via special methods. The mechanism uses **forward and reverse methods** to let operands negotiate who handles the operation — without requiring either to know the other's type.

## Rules for Operator Overloading
1. You cannot change the meaning of operators for built-in types
2. You cannot create new operators (e.g. `<=>`)
3. Some operators cannot be overloaded: `is`, `and`, `or`, `not`
4. Operators should return `NotImplemented` (not raise `TypeError`) when they cannot handle the operand type — this lets Python try the reflected operation on the other operand

## Forward and Reverse Methods
When Python evaluates `a + b`:
1. Calls `a.__add__(b)` — if it returns `NotImplemented`:
2. Calls `b.__radd__(a)` — if that also returns `NotImplemented`:
3. Raises `TypeError`

```python
def __add__(self, other):
    try:
        pairs = zip(self, other)
    except TypeError:
        return NotImplemented
    return Vector(a + b for a, b in pairs)

def __radd__(self, other):
    return self + other   # delegate to __add__
```

## Unary Operators
```python
def __abs__(self):
    return math.hypot(*self)   # magnitude

def __neg__(self):
    return Vector(-x for x in self)

def __pos__(self):
    return Vector(self)        # copy
```

## Scalar Multiplication
```python
def __mul__(self, scalar):
    if isinstance(scalar, (int, float, complex)):
        return Vector(x * scalar for x in self)
    return NotImplemented

def __rmul__(self, scalar):
    return self * scalar       # commutative: delegate
```

## The `@` Matrix Multiplication Operator (Python 3.5+)
Supported via `__matmul__` / `__rmatmul__`:
```python
def __matmul__(self, other):
    if len(self) != len(other):
        raise ValueError('lengths must be equal')
    return sum(a * b for a, b in zip(self, other))  # dot product

def __rmatmul__(self, other):
    return self @ other
```

## Rich Comparison Operators
| Method | Operator | Reflected method |
|---|---|---|
| `__eq__` | `==` | `__eq__` (symmetric) |
| `__ne__` | `!=` | (auto-derived from `__eq__`) |
| `__lt__` | `<` | `__gt__` |
| `__le__` | `<=` | `__ge__` |
| `__gt__` | `>` | `__lt__` |
| `__ge__` | `>=` | `__le__` |

`__ne__` delegates to `__eq__` by default (returns `not self.__eq__(other)`). Define only `__eq__` unless ordering is needed.

Use `functools.total_ordering` to auto-generate all comparison methods from `__eq__` and one of `__lt__`, `__le__`, `__gt__`, `__ge__`.

## Augmented Assignment Operators
`+=` calls `__iadd__` if defined; falls back to `__add__` + rebinding otherwise:
```python
def __iadd__(self, other):
    # Mutable types modify in place and return self
    for val in other:
        self._components.append(val)
    return self
```
Immutable types (like `Vector`) should NOT define `__iadd__` — Python will create a new object via `__add__` and rebind the variable automatically.

## `isinstance` in Operator Methods
Unlike other contexts, `isinstance` checks inside operator methods are acceptable when using **goose typing** to verify operand types. The proper check: return `NotImplemented` for unknown types; raise `TypeError` only when you are certain the operation is semantically wrong.

## `pathlib.Path` and the `/` Operator
A non-arithmetic real-world example:
```python
from pathlib import Path
p = Path('/etc') / 'init.d' / 'reboot'   # PosixPath('/etc/init.d/reboot')
```

## Closing Thoughts
Operator overloading makes user-defined types feel native. The key discipline is: return `NotImplemented` rather than raising `TypeError`, always implement the reflected method, and never change semantics in surprising ways. The `pathlib` `/` operator and NumPy's `@` operator show that operator overloading extends naturally beyond arithmetic.

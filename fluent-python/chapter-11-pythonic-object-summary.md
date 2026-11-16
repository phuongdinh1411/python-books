# Chapter 11 – A Pythonic Object

## Core Idea
A **Pythonic** class integrates naturally with the language: it supports `repr`, `str`, `format`, hashing, comparison, and the iteration protocol by implementing special methods. The goal is not to parade every feature, but to use the minimum set that fulfils real requirements — and to do so correctly.

## Object Representations
Every object should support at least one developer-friendly representation:
- `__repr__` — unambiguous; used in the REPL and `repr()`; ideally evaluable: `repr(v)` looks like `Vector2d(3.0, 4.0)`
- `__str__` — user-friendly; used by `print()` and `str()`; fallback is `__repr__`
- `__format__` — supports the format spec in f-strings: `f'{v:.2f}'`
- `__bytes__` — bytes representation; used by `bytes()`

## Alternative Constructors
```python
@classmethod
def frombytes(cls, octets):
    typecode = chr(octets[0])
    memv = memoryview(octets[1:]).cast(typecode)
    return cls(*memv)
```
`@classmethod` takes `cls` as first argument and is called on the class. `@staticmethod` is just a regular function in a class namespace — prefer module-level functions when there is no relationship to the class.

## `classmethod` vs `staticmethod`
| | `@classmethod` | `@staticmethod` |
|---|---|---|
| First argument | `cls` | none (regular function) |
| Typical use | Alternative constructors | Utility related to class but not needing `cls` or `self` |
| Access to class | Yes | No |

## Formatted Displays
```python
def __format__(self, fmt_spec=''):
    if fmt_spec.endswith('p'):          # polar coordinates
        fmt_spec = fmt_spec[:-1]
        coords = (abs(self), self.angle())
        outer_fmt = '<{}, {}>'
    else:
        coords = self
        outer_fmt = '({}, {})'
    components = (format(c, fmt_spec) for c in coords)
    return outer_fmt.format(*components)
```

## Making an Object Hashable
Hashable objects must satisfy: `a == b → hash(a) == hash(b)`.
- Define `__eq__` and `__hash__` together
- If `__eq__` is defined but not `__hash__`, the class becomes unhashable
- Use `hash(tuple(self))` or XOR individual field hashes

```python
def __hash__(self):
    return hash((self.x, self.y))

def __eq__(self, other):
    return tuple(self) == tuple(other)
```

## Read-Only Attributes with Properties
```python
class Vector2d:
    def __init__(self, x, y):
        self.__x = float(x)   # name-mangled: _Vector2d__x
        self.__y = float(y)

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y
```
Name mangling (`__x`) prevents accidental access from subclasses while `@property` provides clean read access.

## `__slots__`
Replaces `__dict__` with a fixed set of attributes; saves memory significantly for millions of instances:
```python
class Vector2d:
    __slots__ = ('__x', '__y')
```
**Caveats:**
- Subclasses need their own `__slots__` to get the savings
- Instances cannot have arbitrary attributes
- Use only when profiling confirms memory is the bottleneck

## Overriding Class Attributes
Instance attributes shadow class attributes:
```python
class Vector2d:
    typecode = 'd'   # class attribute

v = Vector2d(1, 2)
v.typecode = 'f'     # creates instance attribute, shadows class attribute
Vector2d.typecode    # still 'd'
```

## Closing Thoughts
A well-crafted class uses the minimum set of special methods needed: `__repr__` always, `__str__` when user-facing display differs, `__hash__` + `__eq__` together when objects should be usable as dict keys, and `@property` when attributes need protection or computation. `__format__` and `__bytes__` add polish. `__slots__` is a memory optimisation, not a default.

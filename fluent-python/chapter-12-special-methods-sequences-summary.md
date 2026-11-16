# Chapter 12 – Special Methods for Sequences

## Core Idea
A custom sequence-like class needs only `__getitem__` and `__len__` to gain iteration, slicing, `in`-membership, and `reversed`. Implementing the full protocol correctly — including slicing returning new instances, dynamic attribute access, and hashing — requires understanding how Python dispatches each operation.

## Building a Multi-Dimensional Vector (running example)
The `Vector` class accepts any number of components, implementing the full sequence protocol step-by-step.

## Step 1: Sequence Protocol with `__getitem__` and `__len__`
```python
class Vector:
    def __init__(self, components):
        self._components = array.array('d', components)

    def __len__(self):
        return len(self._components)

    def __getitem__(self, index):
        return self._components[index]
```
Just these two methods give: `v[0]`, `v[-1]`, `for x in v`, `x in v`, `reversed(v)`.

## Step 2: Proper Slicing
`v[1:3]` should return a new `Vector`, not a raw `array`. Detect slices via `isinstance`:
```python
def __getitem__(self, key):
    if isinstance(key, slice):
        cls = type(self)
        return cls(self._components[key])
    return self._components[key]
```

## Step 3: Dynamic Attribute Access
Provide `v.x`, `v.y`, `v.z`, `v.t` for the first four components:
```python
shortcut_names = 'xyzt'

def __getattr__(self, name):
    if len(name) == 1 and name in shortcut_names:
        index = shortcut_names.index(name)
        if index < len(self):
            return self._components[index]
    raise AttributeError(f'{type(self).__name__!r} has no attribute {name!r}')

def __setattr__(self, name, value):
    # Forbid single-letter names to avoid inconsistency with __getattr__
    if len(name) == 1 and name in shortcut_names:
        error = "readonly attribute 'a' to 't'"
        raise AttributeError(error)
    super().__setattr__(name, value)
```
**Rule**: if you implement `__getattr__`, also implement `__setattr__` to prevent asymmetric behaviour.

## Step 4: Hashing with `functools.reduce`
```python
def __hash__(self):
    hashes = (hash(x) for x in self._components)
    return functools.reduce(operator.xor, hashes, 0)   # 0 is identity for XOR

def __eq__(self, other):
    return len(self) == len(other) and all(a == b for a, b in zip(self, other))
```
Use `zip` + `all` instead of comparing full tuples to short-circuit early.

## Step 5: Custom `__format__` with Spherical Coordinates
```python
def __format__(self, fmt_spec=''):
    if fmt_spec.endswith('h'):         # hyperspherical coordinates
        fmt_spec = fmt_spec[:-1]
        coords = itertools.chain([abs(self)], self.angles())
        outer_fmt = '<{}>'
    else:
        coords = self
        outer_fmt = '({})'
    components = (format(c, fmt_spec) for c in coords)
    return outer_fmt.format(', '.join(components))
```

## Duck Typing and Protocols
Python's sequence protocol is informal: implement `__len__` and `__getitem__` and you're treated as a sequence — no inheritance required. This is the essence of **duck typing**.

```python
class Shuffle:
    def __len__(self): return 5
    def __getitem__(self, i): return i * 2

import random
random.shuffle(Shuffle())   # works, even without list inheritance
```

## How Slicing Works Internally
```python
class MySeq:
    def __getitem__(self, index):
        return index   # just return what Python sends

s = MySeq()
s[1:4]      # slice(1, 4, None)
s[1:4:2]    # slice(1, 4, 2)
s[1:4:2, 9] # (slice(1, 4, 2), 9)  — NumPy-style multidimensional
```

## Closing Thoughts
Sequence types illustrate the power of the data model: a dozen carefully implemented special methods give a class complete compatibility with Python's iteration, slicing, and introspection infrastructure. `__getitem__` is the single most important method for sequences. Always return the same type from slices, always pair `__getattr__` with `__setattr__`, and use `functools.reduce` + `operator.xor` for elegant aggregate hashing.

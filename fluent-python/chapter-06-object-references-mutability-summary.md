# Chapter 6 – Object References, Mutability, and Recycling

## Core Idea
Python variables are **labels attached to objects**, not boxes that contain values. This mental model is essential for understanding assignment, copying, equality vs. identity, and how mutable arguments behave inside functions.

## Variables Are Labels, Not Boxes
```python
a = [1, 2, 3]
b = a         # b is another label on the SAME list
b.append(4)
a             # [1, 2, 3, 4]  — a and b see the same object
```
Assignment never copies an object. It binds a name to an existing object.

## Identity vs. Equality
- `==` calls `__eq__`: tests **value** equality
- `is` tests **identity**: whether two names refer to the exact same object
```python
a = [1, 2]
b = [1, 2]
a == b    # True  (same value)
a is b    # False (different objects)
```
`is` is appropriate for comparing against singletons: `x is None`, `x is True`.

## The Relative Immutability of Tuples
Tuple elements cannot be reassigned, but if an element is a mutable object, the object itself can change:
```python
t = (1, 2, [30, 40])
t[2].append(50)   # OK — list inside tuple mutated
t                 # (1, 2, [30, 40, 50])
```

## Copies Are Shallow by Default
```python
import copy
l1 = [[1, 2], [3, 4]]
l2 = list(l1)         # shallow copy
l2[0].append(99)
l1[0]                 # [1, 2, 99]  — inner list shared!

l3 = copy.deepcopy(l1)  # deep copy: new objects recursively
```
Shallow copies are made by: slices (`a[:]`), `list(a)`, `dict(d)`, `copy.copy()`.

## Function Parameters as References
Python uses **call by sharing**: functions receive copies of references to objects, not copies of objects themselves.
```python
def append_one(lst):
    lst.append(1)     # mutates the original

a = [0]
append_one(a)
a   # [0, 1]
```

### Mutable Defaults Are Dangerous
```python
def add_item(item, bag=[]):   # WRONG: shared mutable default
    bag.append(item)
    return bag

add_item('a')  # ['a']
add_item('b')  # ['a', 'b']  — same list reused!
```
Fix: use `None` as default and create a new list inside the function.

### Defensive Copies
If a function must not let callers mutate its internal state:
```python
class Bus:
    def __init__(self, passengers=None):
        if passengers is None:
            self.passengers = []
        else:
            self.passengers = list(passengers)  # copy the input
```

## `del` and Garbage Collection
`del` removes a **reference** (a name binding), not the object. The object is garbage-collected only when no more references remain.
- CPython uses **reference counting** with a supplementary cycle-detecting GC
- `__del__` is called just before the object is destroyed (use sparingly; avoid cycles)
- Use `weakref.ref()` to hold a reference that does not prevent GC

## Python Tricks with Immutables (Interning)
CPython interns small integers (typically -5 to 256) and many short strings. `a is b` may unexpectedly return `True` for these values. Never rely on `is` for equality of immutable literals; always use `==`.

## Closing Thoughts
The reference model means: every assignment is cheap (just a pointer copy), mutation through aliases is always possible with mutable objects, and accidental sharing is the most common source of subtle bugs. Defensive copies and `None`-as-default patterns are the primary antidotes.

# Chapter 3 – Dictionaries and Sets

## Core Idea
`dict` and `set` are hash-table–based structures that offer O(1) average-case lookup. Understanding their internals — what hashability means, how keys are stored, and the full mapping API — prevents bugs and unlocks idiomatic Python.

## Modern `dict` Syntax
```python
# dict comprehension
prices = {code: price for code, price in data}

# unpacking with **
merged = {**defaults, **overrides}

# merge operator (Python 3.9+)
combined = d1 | d2      # new dict
d1 |= d2                # update d1 in place
```

## Pattern Matching with Mappings
```python
match record:
    case {'action': action, 'object': obj}:
        handle(action, obj)
```
Matching extracts named keys; extra keys in the subject are ignored.

## Hashability
An object is **hashable** if it has a `__hash__()` that never changes during its lifetime, and a `__eq__()` consistent with it.
- All built-in immutables are hashable
- `tuple` is hashable only if all items are hashable
- User-defined instances are hashable by default (based on `id`)
- Lists, dicts, sets are **not** hashable

## Key Mapping Methods
| Method | Effect |
|---|---|
| `d.setdefault(key, default)` | Returns value if key exists; inserts default and returns it otherwise |
| `d.get(key, default)` | Returns value or default; does not insert |
| `d.update(other)` | Bulk insert/overwrite from mapping, iterable of pairs, or kwargs |
| `d.pop(key, default)` | Remove and return; raises `KeyError` without default |
| `d.popitem()` | Remove and return last-inserted pair (LIFO) |
| `d \| other` | Return new dict merged (Python 3.9+) |

## Handling Missing Keys
```python
# defaultdict: automatically creates missing values
index = collections.defaultdict(list)
for word, page in data:
    index[word].append(page)

# __missing__: customize d[key] when key absent
class StrKeyDict(dict):
    def __missing__(self, key):
        if isinstance(key, str):
            raise KeyError(key)
        return self[str(key)]  # try string version
```

## Mapping Variants
| Class | Purpose |
|---|---|
| `dict` | General-purpose hash map; insertion-ordered since 3.7 |
| `collections.OrderedDict` | Key order matters for equality comparison |
| `collections.ChainMap` | Layered lookup through multiple dicts |
| `collections.Counter` | Counts hashable objects; most_common(), arithmetic |
| `collections.UserDict` | Base class for custom mappings (subclass this, not `dict`) |
| `types.MappingProxyType` | Read-only view of a mapping |

## Dictionary Views
`d.keys()`, `d.values()`, `d.items()` return **live views** that reflect mutations:
```python
d = {'a': 1, 'b': 2}
keys = d.keys()
d['c'] = 3
list(keys)  # ['a', 'b', 'c']  — view updated automatically
```
`dict_keys` and `dict_items` support set operators (`&`, `|`, `-`, `^`):
```python
d1.keys() & d2.keys()   # keys in both dicts
d1.keys() | {'x', 'y'}  # union with a set
```

## Set Theory
Sets are unordered collections of unique hashable objects.
```python
s = {1, 2, 3}         # set literal (not empty — {} makes a dict)
empty = set()
s2 = {x**2 for x in range(5)}  # set comprehension
```

### Set Operations
| Operator | Method | Description |
|---|---|---|
| `a & b` | `a.intersection(b)` | Common elements |
| `a \| b` | `a.union(b)` | All elements |
| `a - b` | `a.difference(b)` | In a but not b |
| `a ^ b` | `a.symmetric_difference(b)` | In one but not both |

`frozenset` is the immutable, hashable variant of `set` (usable as dict key or set element).

## Practical Consequences of Hash Tables
- Keys must be hashable; equality and hash must be consistent
- Dict lookup is O(1) average but memory-intensive (sparse table)
- Key insertion order is preserved (Python 3.7+)
- Avoid mutating a dict while iterating over it

## Closing Thoughts
Dicts and sets underpin much of Python. The `setdefault`/`__missing__` hooks, the `defaultdict` class, and set operators on dict views are all tools that reduce boilerplate. Choose the right mapping variant for the job: `Counter` for tallying, `ChainMap` for layered configuration, `UserDict` when subclassing.

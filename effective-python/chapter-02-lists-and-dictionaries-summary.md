# Chapter 2 – Lists and Dictionaries

## Core Idea
Lists and dictionaries are Python's most-used data structures. Python provides rich, expressive syntax and built-in tools that go well beyond basic array/hash-table operations. Using them correctly avoids common bugs and makes code far more readable.

## Items Summary

### Item 11: Know How to Slice Sequences
- Syntax: `a[start:end]` — `start` inclusive, `end` exclusive
- Omit `0` from the start: `a[:5]` not `a[0:5]`
- Omit `len(a)` from the end: `a[5:]` not `a[5:len(a)]`
- Negative indices count from the end: `a[-3:]` = last 3 items
- Slicing never raises `IndexError` — it clamps to boundaries
- Assigning to a slice replaces elements, even with different length: `a[2:5] = [99]`

### Item 12: Avoid Striding and Slicing in a Single Expression
- `a[::2]` strides by 2; `a[::-1]` reverses
- Combining stride with start/end is hard to read: `a[2:10:2]`
- **Rule**: if you need both a slice and a stride, do it in two steps:
  ```python
  evens = a[::2]
  sliced = evens[1:-1]
  ```

### Item 13: Prefer Catch-All Unpacking Over Slicing
- Starred expressions capture "the rest" when unpacking:
  ```python
  first, *middle, last = [1, 2, 3, 4, 5]
  # first=1, middle=[2,3,4], last=5
  ```
- Clearer and less brittle than index-based slicing
- The starred portion is always a `list`, even if empty

### Item 14: Sort by Complex Criteria Using the `key` Parameter
- `list.sort(key=...)` and `sorted(..., key=...)` take a function returning a sort value
  ```python
  people.sort(key=lambda p: p.last_name)
  ```
- **Tuple trick for multi-key sort**: sort by primary key, then secondary:
  ```python
  items.sort(key=lambda x: (x.weight, x.name))
  ```
- Negate numeric fields for descending within a tuple: `(-x.weight, x.name)`
- For non-numeric fields requiring mixed direction, call `sort` twice (stable sort)

### Item 15: Be Cautious When Relying on `dict` Insertion Ordering
- Python 3.7+: `dict` preserves insertion order — guaranteed by the language spec
- The real pitfall is accepting a general mapping while assuming it has `dict` ordering: a custom mapping may iterate differently
- Use a concrete `dict` contract or sort explicitly when your algorithm requires a particular order
- `OrderedDict` is useful for order-specific operations such as `move_to_end` and order-sensitive equality, not required merely to preserve insertion order

### Item 16: Prefer `get` Over `in` and `KeyError` to Handle Missing Dictionary Keys
- Three patterns, ranked worst to best:
  ```python
  # 1. Bad: two lookups
  if key in d:
      value = d[key]

  # 2. OK: try/except — fine for read-heavy code
  try:
      value = d[key]
  except KeyError:
      value = default

  # 3. Best: get with default
  value = d.get(key, default)
  ```
- For mutable defaults (lists, dicts), use `setdefault` or `defaultdict` (see Items 17/18)

### Item 17: Prefer `defaultdict` Over `setdefault` to Handle Missing Items in Internal State
- `setdefault` is awkward: it always creates the default value, even when the key exists
- `defaultdict(list)` automatically creates missing keys with the factory value:
  ```python
  from collections import defaultdict
  visits = defaultdict(list)
  visits["Alice"].append("Paris")
  ```
- Cleaner, faster, and more Pythonic for internal bookkeeping

### Item 18: Know How to Construct Key-Dependent Default Values with `__missing__`
- `defaultdict` factory receives no arguments — can't create a value based on the key
- Subclass `dict` and override `__missing__` when the default depends on the key:
  ```python
  class PictureDict(dict):
      def __missing__(self, key):
          value = open_picture(key)
          self[key] = value
          return value
  ```
- Use `__missing__` only when the default is key-dependent; prefer `defaultdict` otherwise

## Key Takeaways
- Use slicing idioms consistently — omit zero/len, don't mix stride with start/end
- Starred unpacking beats index-based slicing for readability
- Use `get()` and `defaultdict` to handle missing keys cleanly
- Understand `dict` ordering but don't abuse it

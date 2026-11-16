# Chapter 2 – An Array of Sequences

## Core Idea
Python's sequence types share a rich common interface. Choosing the right sequence type — and understanding its behaviour with slicing, unpacking, augmented assignment, and pattern matching — makes code clearer and avoids subtle bugs.

## Sequence Taxonomy

| Category | Types | Key property |
|---|---|---|
| **Container** | `list`, `tuple`, `deque`, `collections.deque` | Hold references to objects of any type |
| **Flat** | `str`, `bytes`, `bytearray`, `array.array`, `memoryview` | Store values contiguously in memory (more compact) |
| **Mutable** | `list`, `bytearray`, `array.array`, `deque` | Can be changed in place |
| **Immutable** | `tuple`, `str`, `bytes` | Cannot be changed after creation |

## List Comprehensions and Generator Expressions
Listcomps are clearer than `map`/`filter` chains for most tasks:
```python
symbols = '$¢£¥€¤'
codes = [ord(s) for s in symbols if ord(s) > 127]  # listcomp
codes = list(filter(lambda c: c > 127, map(ord, symbols)))  # equivalent but harder to read
```
**Generator expressions** produce items one at a time and avoid materialising the full list in memory:
```python
sum(ord(s) for s in symbols)  # no intermediate list
```

## Tuples as Records vs Immutable Lists
- **As records**: tuple position carries meaning (`city, year, pop = ('Tokyo', 2003, 32_450_000)`)
- **As immutable lists**: better performance, clear intent that sequence won't change
- Tuples support all list methods except those that mutate (no `append`, `sort`, etc.)

## Unpacking
```python
a, b = (1, 2)                   # basic unpacking
a, *rest = range(5)             # grab excess with *
first, *middle, last = range(5) # middle catches [1,2,3]
```
Unpacking works with any iterable; `*` can appear in any position. Nested unpacking is also supported.

## Pattern Matching with Sequences (Python 3.10+)
```python
match command:
    case ['quit']:
        quit_game()
    case ['move', direction]:
        move(direction)
    case ['drop', *objects]:
        for obj in objects: drop(obj)
```
- Patterns are matched against structure, not just equality
- `*extra` in a pattern captures remaining items as a list

## Slicing
- `seq[start:stop:step]` — stop is always excluded (consistent with `range()`)
- `s[a:b:c]` creates a `slice(a, b, c)` object passed to `__getitem__`
- Slices can be assigned to mutable sequences: `deck[0:2] = [new1, new2]`
- Named slices improve readability: `PRICE = slice(10, 17)`

## `+` and `*` Gotcha with Lists
```python
# WRONG: creates list of 3 references to the SAME inner list
board = [['_'] * 3] * 3

# RIGHT: each row is a distinct list
board = [['_'] * 3 for _ in range(3)]
```

## Augmented Assignment Puzzle
```python
t = (1, 2, [30, 40])
t[2] += [50, 60]  # raises TypeError — but also modifies t[2] in-place!
```
The in-place `+=` on the list succeeds, but assigning back to the tuple position fails. Avoid mutable items inside tuples.

## `list.sort` vs `sorted`
- `list.sort()` sorts **in place**, returns `None`
- `sorted()` returns a **new sorted list**, works on any iterable
- Both accept `key=` (function) and `reverse=` (bool)

## When Not to Use a List
| Alternative | Use when |
|---|---|
| `array.array` | Millions of floats; compact C-level storage |
| `memoryview` | Need to inspect/edit bytes of another object without copying |
| `numpy.ndarray` | Numerical computing, matrix operations |
| `collections.deque` | Fast O(1) appends/pops from both ends |

## Closing Thoughts
Python's sequence types are not interchangeable. Choose `tuple` when you want an immutable record, `array.array` for packed numeric data, and `deque` for queues. The rich shared interface — slicing, unpacking, pattern matching — applies widely, but subtle behaviours (mutable defaults, augmented assignment on immutables) must be understood to avoid surprises.

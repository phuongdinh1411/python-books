# Chapter 3 Summary: Lists and Tuples
*High Performance Python, 3rd Edition*

---

## Core Concept: Arrays in Python

Both lists and tuples are **arrays** — flat, ordered collections stored in contiguous memory as integer-sized **pointers** to actual data. Because of this layout:
- **Lookup by index** is always **O(1)** — find element `i` at memory address `M + i`, regardless of array size
- This holds whether the array has 10 or 10,000,000 elements (confirmed by timing benchmarks)

---

## Searching: The Cost of Unknown Order

| Scenario | Algorithm | Complexity |
|---|---|---|
| Index known | Direct lookup | O(1) |
| Sorted data | **Binary search** | O(log n) |
| Unsorted data | Linear search | O(n) |

### Binary Search (`bisect` module)
Python's `bisect` standard library provides:
- `bisect.insort()` — insert while maintaining sort order
- `bisect.bisect_left()` — fast O(log n) search
- Useful for finding the **closest** element to a value

**Key rule**: pick the right data structure and stick with it. Converting data to a dict for a single O(1) lookup may cost more in O(n) conversion than just doing an O(log n) binary search on a sorted list.

---

## Lists vs. Tuples

| Property | List | Tuple |
|---|---|---|
| Mutability | Mutable (resizable) | Immutable (fixed) |
| Memory | Extra overhead for resize headroom | Exact size only |
| Creation speed | Depends on construction and interpreter | Often cheaper for fixed records; literal benchmarks may reuse constants |
| Allocation reuse | Implementation-dependent | Implementation-dependent; some CPython versions use tuple freelists |
| Use case | Growing/changing collections | Fixed, multi-property records |

---

## Lists as Dynamic Arrays

Lists support resizing via **overallocation** — when appended to, Python allocates extra space to avoid frequent reallocations:

```python
M = (N + (N >> 3) + 6) & ~3   # Python 3.12 allocation formula
```

- Generally overallocates ~**12.5%** extra space
- Small lists can overallocate much more (4 slots for 1 item, 16 for 9 items)
- A list of 100,000,000 elements built with appends actually allocates **104,391,068** slots

### Memory Impact of Overallocation
Creating 1,000,000 samples of 9 items each:
- List comprehension (overallocated): **444 MB**
- `list(...)` re-wrap (no overallocation): **396 MB** (1.12× smaller)
- `tuple(...)`: **372 MB** (1.19× smaller)

> Tip: If building many small lists that won't grow, wrap them with `list()` or `tuple()` to strip the overallocation headroom.

---

## Tuples as Static Arrays

Tuples are immutable — they **cannot** be resized or modified after creation. Key advantages:

### 1. Lower Memory Footprint
- No overallocation headroom
- Slightly smaller base overhead than lists
- Savings add up significantly when holding millions of tuples

### 2. Allocation Reuse (Implementation Detail)
- Some CPython versions reuse storage for small, freed tuples through freelists
- This is storage reuse, not a cache of tuple values; capacities and behavior vary by version/build
- Literal-tuple timings may measure reuse of a compiled constant rather than creation. Benchmark the actual construction pattern before claiming a speedup.

### When to Use Each
- **Tuple**: phone number parts, polynomial coefficients, a person's birthday & birthplace, a single game's result — static, multi-field records
- **List**: names of languages, people's mutable attributes, an ongoing series of results — growing or changing collections

---

## Key Takeaways

1. O(1) lookups are possible only when the index is known; otherwise search algorithms are needed
2. Sorting + binary search (`bisect`) is the efficient middle ground between O(n) linear search and O(1) dict lookups
3. Lists overallocate memory to support cheap appends — be mindful with many small lists
4. Tuples usually have less container overhead and express fixed structure; referenced mutable objects can still change. Choose by semantics, then measure memory and construction cost.
5. Both support mixed types, but mixed types sacrifice potential optimizations (see numpy in Ch. 6)

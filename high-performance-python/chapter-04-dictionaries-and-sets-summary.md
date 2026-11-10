# Chapter 4 Summary: Dictionaries and Sets
*High Performance Python, 3rd Edition*

---

## Core Concept: Hash Tables

Dictionaries and sets use hash tables for **average O(1)** lookup, insertion, and deletion, assuming well-distributed hashes and bounded hash/equality cost. Collisions can degrade operations to O(n). Sets store unique elements without associated values; their layout differs from dictionaries.

| Data Structure | Lookup | Insert | Use Case |
|---|---|---|---|
| List (unsorted) | O(n) | O(1) amortized | Ordered, index-based data |
| List (sorted) + bisect | O(log n) | O(n) | Searchable ordered data |
| Dict / Set | **O(1) average** | **O(1) amortized average** | Key-indexed or unique data |

**Example**: finding unique first names in a phone book — set approach was **560× faster** (O(n) vs O(n log n)) for 10,000 entries, and **4,300× faster** for 100,000 entries.

---

## How Hash Tables Work

### Inserting a Key-Value Pair
1. Compute `hash(key)` → apply a **bit mask** to fit within allocated buckets
   - e.g., for 8 buckets, `mask = 0b111`; index = `hash(key) & mask`
2. If bucket is empty → store key + value
3. If bucket is occupied → **probe** for next free slot using a perturbation scheme:
   ```python
   perturb >>= PERTURB_SHIFT   # 5
   i = (i * 5 + perturb + 1) & mask
   ```
4. This probing uses higher-order bits of the hash to reduce collision chains

> Optimization: Python actually stores key/value data in a separate dense array and only stores the **index** into that array in the hash table. This reduces memory by 30–95% and preserves **insertion order** (guaranteed since Python 3.7).

### Lookup
Same process: hash the key → check bucket → if key matches, return value; if not, probe until found or empty bucket hit (→ key not present).

### Deletion
Cannot simply write NULL (would break collision probing). Instead, writes a **sentinel value** marking the slot as "was occupied." Actual cleanup happens on resize.

### Resizing
- CPython keeps spare hash-table capacity to limit probing; dict and set load policies differ
- Table sizes, growth formulas, and compaction behavior are implementation details that change between versions
- Rebuilding rehashes existing entries: expensive for that insertion, but average insertion cost is amortized O(1)
- Deleting entries usually does not immediately shrink the allocated table; avoid assuming a particular insertion will reclaim memory

---

## Hash Functions and Entropy

A good hash function distributes keys uniformly across buckets (**high entropy**). Poor hash functions lead to collisions → O(n) degradation.

### Built-in Types
- **Integers**: small integer hashes usually equal the value; large integers are reduced modulo an implementation-specific modulus, and `hash(-1) == -2`
- **Strings/bytes**: modern CPython uses randomized hashing (commonly SipHash); tuple hashing combines the element hashes using a different algorithm
- **Lists**: not hashable; mutable contents do not support a stable value hash
- **User classes**: default equality and hashing are identity-based; the hash is not simply `id(obj)`

### Custom Hash Functions
If two objects should be equal (e.g., two `Point(1,1)` instances), define `__hash__` and `__eq__`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: int
    y: int
```

Without value equality, two `Point(1,1)` objects would be treated as different keys. Equal objects must have equal hashes, and hash-relevant state must stay stable while used as a key. This frozen dataclass generates consistent equality and hashing for its integer fields.

### Entropy Formula
```
S = -∑ pᵢ · log(pᵢ)
```
Maximized when all hash values are equally probable. An "ideal" hash function yields the minimum number of collisions.

### Timing Impact of Hash Quality
For a set of 676 two-letter keys:
| Hash Quality | Lookup time |
|---|---|
| Bad hash (always returns 42) | 10.16 s |
| Good hash (optimal for 2-letter keys) | 0.187 s (**54× faster**) |
| List lookup (control) | 8.96 s |

> A bad enough hash function can make a dictionary **slower than a linear search through a list**.

---

## Memory Layout

- Dicts and sets use different layouts and reserve unused capacity to support fast probing
- Exact bucket counts, load thresholds, and per-entry overhead depend on CPython version/build
- Measure the actual structure rather than assuming most allocated memory is always empty

---

## Key Takeaways

1. Dicts and sets give average O(1) lookup at the cost of memory and hash/equality overhead
2. Hashing quality is critical — a bad `__hash__` can reduce a dict to O(n) performance
3. Always define both `__hash__` and `__eq__` together when creating hashable custom objects
4. Deletion uses sentinels; actual memory is reclaimed on resize
5. Insertion order is preserved in all Python dicts since 3.7
6. When building millions of lookups with custom types, test your hash function's entropy

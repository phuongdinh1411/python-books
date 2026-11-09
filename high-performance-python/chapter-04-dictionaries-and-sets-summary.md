# Chapter 4 Summary: Dictionaries and Sets
*High Performance Python, 3rd Edition*

---

## Core Concept: Hash Tables

Dictionaries and sets use **open-address hash tables** to achieve **O(1)** lookups, insertions, and deletions — regardless of size. Sets are essentially dictionaries without values (just unique keys).

| Data Structure | Lookup | Insert | Use Case |
|---|---|---|---|
| List (unsorted) | O(n) | O(1) amortized | Ordered, index-based data |
| List (sorted) + bisect | O(log n) | O(n) | Searchable ordered data |
| Dict / Set | **O(1)** | **O(1) amortized** | Key-indexed or unique data |

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
- Dictionary is always kept **≤ 2/3 full** (sets: ≤ 3/5 full)
- Always sized as a **power of two** (minimum size: 8)
- When threshold exceeded, resize to 3× current size → round up to next power of two
- Resizing copies all existing entries into the new table (expensive but amortized O(1) per insert)
- Resizing can also shrink the table — triggered on the next **insert** after many deletions

---

## Hash Functions and Entropy

A good hash function distributes keys uniformly across buckets (**high entropy**). Poor hash functions lead to collisions → O(n) degradation.

### Built-in Types
- **Integers**: hash = the integer itself (ideal for infinite table)
- **Strings/Tuples**: hash based on all contents (using SipHash 1-3)
- **Lists**: not hashable (mutable → hash could change)
- **User classes**: default hash = memory address (`id(obj)`)

### Custom Hash Functions
If two objects should be equal (e.g., two `Point(1,1)` instances), define `__hash__` and `__eq__`:

```python
class Point:
    def __hash__(self):
        return hash((self.x, self.y))
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
```

Without this, two `Point(1,1)` objects would be treated as different keys in a set.

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

- Minimum dictionary/set size: **8 buckets**
- Always at least **1/3 empty** (for sets, 2/5 empty)
- Most of the memory in a hash table is empty — this is by design for performance

---

## Key Takeaways

1. Dicts and sets give O(1) lookup at the cost of higher memory usage and hash function overhead
2. Hashing quality is critical — a bad `__hash__` can reduce a dict to O(n) performance
3. Always define both `__hash__` and `__eq__` together when creating hashable custom objects
4. Deletion uses sentinels; actual memory is reclaimed on resize
5. Insertion order is preserved in all Python dicts since 3.7
6. When building millions of lookups with custom types, test your hash function's entropy

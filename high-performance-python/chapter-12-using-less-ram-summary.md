# Chapter 12 Summary: Using Less RAM
*High Performance Python, 3rd Edition*

---

## Why RAM Matters

Running out of RAM forces the OS to swap to disk — **all performance gains from optimization vanish instantly**. Fitting data in RAM means avoiding clusters. Even within RAM, poor memory layout causes cache misses and slows computation.

---

## Primitives Are Expensive

Python's integer objects have significant overhead:
- A Python `int` holding 0 costs **28 bytes** (vs. 8 bytes for a C `int64`)
- A Python `float` costs **24 bytes** (vs. 8 bytes for C `double`)

### `array` Module for 1D Primitive Arrays
```python
from array import array
arr = array('l', range(1_000_000))   # typed, contiguous memory
```
- Stores raw C types (1/4 the size of a Python list of ints)
- But: accessing elements still boxes them back into Python objects → not faster for iteration

### NumPy for Compact Typed Arrays
```python
import numpy as np
arr = np.arange(1_000_000, dtype=np.int32)   # 4 bytes per element
```
- Vectorized operations avoid per-element Python overhead
- Choosing the right dtype saves significant RAM

---

## NumExpr for Large Vector Calculations

NumPy's intermediate array problem: `a * b + c` creates a full temporary array.

**NumExpr** breaks expressions into chunks that fit in CPU cache:
```python
import numexpr
answer = numexpr.evaluate("-(yt * log(yp) + ((1-yt) * (log(1-yp))))")
```

- **16× less peak RAM** (no intermediate arrays)
- **17× faster** for 200M-element arrays (parallelized across cores)
- `df.eval(expr)` in Pandas uses NumExpr automatically **if installed** (install it!)
- Without NumExpr, `df.eval` is **5× slower and uses 4× more RAM**

---

## `sys.getsizeof` Gotcha

`sys.getsizeof` reports **only the container size**, not contents:
```python
sys.getsizeof([b"abcdefghijklm"]) == sys.getsizeof([b""])  # both 64 bytes!
```

Better tools:
- `pympler.asizeof.asizeof(obj)` — recursively estimates full size
- `%memit expression` — measures actual process RAM growth (most reliable)

---

## Bytes vs. Unicode

CPython's PEP 393 string representation uses 1, 2, or 4 bytes per code point depending on the largest code point in a string; object headers add overhead. ASCII `str` and `bytes` both use one byte per character in their payload, but their total sizes differ. This is **not UTF-8 storage**.
```python
import sys

sys.getsizeof("u" * 100_000)  # one-byte payload plus str header
sys.getsizeof("Σ" * 100_000)  # two-byte payload plus str header
sys.getsizeof(b"u" * 100_000) # one-byte payload plus bytes header
```

---

## Efficiently Storing Text: Tries

For 12 million unique Wikipedia tokens, RAM usage comparison:

| Container | RAM | Lookup Time |
|---|---|---|
| `list` (unsorted) | 884 MB | >3 hours (O(n)) |
| `list` + `bisect` | 884 MB | 0.06 s (O(log n)) |
| `set` | 1,300 MB | 0.011 s (O(1)) |
| `dict` | 1,643 MB | 0.010 s (O(1)) |
| **Marisa trie** | 440 MB (build) → **39 MB (loaded)** | 0.06 s |

### Marisa Trie
```python
import marisa_trie
words_trie = marisa_trie.Trie(text_example.readers)
words_trie.save("words.marisa")
# Later:
words_trie = marisa_trie.Trie()
words_trie.load("words.marisa")
```
- **Static** (build once, read many) — ideal for production lookup services
- Supports prefix search (find all words starting with "ta")
- Real-world case: UK postcode geocoder for 1.7M postcodes in **30 MB** (vs. hundreds of MB for a dict)

**DAWG**: shares both prefixes and suffixes → even more RAM efficient but less flexibility for value assignment.

---

## Probabilistic Data Structures

When exact answers aren't required, probabilistic structures offer massive RAM savings:

### Morris Counter (Approximate Counting)
- Stores only a **5-bit counter** instead of an exact integer
- Tracks approximate count with increasing error at higher values
- Cannot deduplicate — counts total insertions, not unique ones

### K-Minimum Values (KMinValues)
- Tracks the `k` smallest hash values seen
- Answers "how many unique items?" with tunable error
- Also supports **set union and intersection** across multiple KMV structures
- Error: O(√(2π/m)) where m = number of stored values

### Bloom Filter (Approximate Set Membership)
```python
bloom = BloomFilter(capacity=100, error=0.005)
bloom.add("item")
"item" in bloom   # True (no false negatives; some false positives)
```
- Fixed capacity, fixed error rate
- **False positives possible**, false negatives impossible
- Supports union (but not intersection reliably)
- Use **Scalable Bloom Filter** to handle unknown dataset sizes
- Use **Timing Bloom Filter** for expiring old entries (stream processing)
- Cuckoo filter: better deletion support, more space-efficient at similar loads

### HyperLogLog (Approximate Cardinality)
- Answers "how many unique items have we seen?"
- Error: O(1.04/√m) where m = number of registers
- Uses only **kilobytes** for hundreds of millions of unique items
- Supports **union** operations
- Evolved from LogLog → SuperLogLog → HyperLogLog → HyperLogLog++

### Illustrative Memory Comparison for 100M Unique Elements

Cardinality sketches use **relative standard error**; Bloom filters use **false-positive probability**. These are different metrics, so the rows below must not be read as sharing a single "0.05% error" guarantee. Exact memory figures depend on parameters, implementation, and element types.

| Structure | RAM | Operations |
|---|---|---|
| HyperLogLog | 2.7 MB | Count unique; union |
| KMinValues | 20 MB | Count unique; union; intersection |
| Bloom filter | 198 MB | Membership test; union |
| Exact `set` | ~1.3 GB | Everything, exact |

---

## Key Takeaways

1. Try NumExpr for supported large expressions; ordinary NumPy operations do not automatically use it, and speed/memory gains depend on expression and array size
2. Use `%memit` (not `sys.getsizeof`) to measure actual RAM usage
3. For large string collections, **Marisa trie** reduces 1.3 GB (set) to 39 MB (loaded trie)
4. Probabilistic structures trade small error guarantees for orders-of-magnitude RAM savings
5. Choose your data structure based on the **specific questions** you need to answer — cardinality? membership? intersection?
6. Fitting data in RAM avoids the need for clustering — a cheaper engineering solution
7. NumPy dtype selection matters: `float32` vs `float64`, `int8` vs `int64` — profile before choosing

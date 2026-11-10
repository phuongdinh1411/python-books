# Chapter 5 Summary: Iterators and Generators
*High Performance Python, 3rd Edition*

---

## Core Concept: Lazy Evaluation

Generators allow Python to **lazily evaluate** sequences — producing values one at a time on demand rather than computing and storing all values upfront. This saves memory and can speed up programs.

```python
# List-based: computes ALL values first, stores in memory
def fibonacci_list(n):
    numbers = []
    a, b = 0, 1
    while len(numbers) < n:
        numbers.append(a)
        a, b = b, a + b
    return numbers

# Generator: computes ONE value at a time on demand
def fibonacci_gen(n):
    a, b = 0, 1
    while n:
        yield a          # pauses here, resumes on next()
        a, b = b, a + b
        n -= 1
```

### Measured Difference (100,000 Fibonacci numbers)
| Approach | Time | Memory |
|---|---|---|
| `fibonacci_list` | 227 ms | **418 MB** |
| `fibonacci_gen` | 82 ms | **~0 MB** |

**These timings depend on consuming the generator without retaining its output.** Generators avoid a stored sequence, not all memory use: Fibonacci integers themselves grow with `n`, so this example is not strictly constant-byte memory.

---

## How Generators Work

- A `yield` statement turns a function into a **generator function**
- Each call to `next()` resumes execution from where `yield` last paused
- A `StopIteration` exception is raised when the generator is exhausted
- Python `for` loops call `iter()` then `next()` repeatedly under the hood

For lists, `iter()` creates a new list-iterator object. For generators, `iter()` is a no-op — they are already iterators.

---

## When NOT to Use Generators

Generators cannot:
- Be iterated more than once (single-pass / online algorithms only)
- Be indexed or sliced directly
- Have their length checked with `len()`

If data needs to be referenced multiple times, a precomputed list may be faster (trades memory for speed).

### CPU vs. Memory Trade-off
> **More memory (precomputed list)** → faster if data is reused  
> **Less memory (generator)** → better for single-pass or large datasets that don't fit in RAM

---

## Common Pitfalls

### Anti-pattern: generator into list comprehension (defeats the purpose)
```python
# WRONG: creates a full list in memory just to get the length
divisible = len([n for n in fibonacci_gen(100_000) if n % 3 == 0])  # ~98 MB

# RIGHT: streams the count without storing all matching numbers
divisible = sum(1 for n in fibonacci_gen(100_000) if n % 3 == 0)
```

### Anti-pattern: `( )` vs `[ ]` in comprehensions
- `[x for x in seq]` → **list** (eager, all in memory)
- `(x for x in seq)` → **generator** (lazy, one at a time)

---

## Infinite Generators

Generators can represent **infinite sequences** — something impossible with lists:

```python
def fibonacci():
    i, j = 0, 1
    while True:
        yield i
        i, j = j, i + j
```

Use `itertools.takewhile` to terminate gracefully:
```python
from itertools import takewhile
first_5000 = takewhile(lambda x: x < 5000, fibonacci())
```

---

## `itertools` — Key Tools for Generators

| Function | Description |
|---|---|
| `islice` | Slice a potentially infinite generator |
| `chain` | Chain multiple generators together |
| `takewhile` | Stop when a condition becomes False |
| `cycle` | Repeat a finite generator infinitely |
| `groupby` | Group consecutive elements by a key |
| `filterfalse` | Yield items that fail a predicate |
| `count` | Infinite counter |

---

## Real-World Example: Anomaly Detection on Large Time-Series Data

Processing 630 million data points (20 years at 1/second) that won't fit in memory:

```python
# Chain of lazy generators
data = read_data("filename")            # yields Datum objects one by one
daily_groups = groupby_day(data)        # groups into day-sized chunks
anomalies = filter_anomalous_groups(daily_groups)  # filters non-normal days
first_five = islice(anomalies, 5)       # stop after 5 results
```

Benefits:
- Only reads as much data as needed (early termination)
- Memory use = **one day's worth of data** at a time
- Easy to swap window functions (daily → rolling window) without restructuring code

### Separation of Concerns with Generators
Generators naturally enforce a two-phase design:
1. **Generator function** → responsible for *producing* data
2. **Normal function** → responsible for *transforming* data

This makes code more modular, testable, and parallelizable.

---

## `collections.deque` for Sliding Windows

For rolling-window generators, `deque` gives O(1) append/pop from both ends:
- `list.append` + `list.pop(0)` → O(n) per step
- `deque.append` + `deque.popleft()` → **O(1)** per step

> Caveat: in-place mutations to the deque destroy previous views, so you'd need to copy to a tuple before yielding — which can negate the benefit. Profile before optimizing.

---

## Key Takeaways

1. Generators produce values lazily → massive memory savings for large or one-pass datasets
2. Use generator comprehensions `(...)` instead of list comprehensions `[...]` where possible
3. `itertools` is the standard library for composing generators — learn it well
4. Generators naturally separate data *generation* from data *transformation*
5. They prepare code for parallelism: once you understand the state each iteration needs, distributing it across cores becomes straightforward (Ch. 9 & 10)
6. Always weigh the CPU/memory trade-off: sometimes precomputing beats laziness if data is reused

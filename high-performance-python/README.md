# High Performance Python — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how can you make Python meet a real speed or memory target without guessing?

**Answer:** measure a representative workload, identify its limiting resource, reduce unnecessary work and data movement, then choose specialized libraries, compilation, or parallel execution if needed.

**Mental model:** correctness baseline → profile → bottleneck hypothesis → one change → validate results → benchmark again.

**Edition:** the chapter notes identify the third edition. Their numerical tables have not been independently reproduced or checked against the book; use them to understand possible mechanisms, not predict your own speedup.

## Quick Route (About 30–45 Minutes)

1. [Ch. 1: Performance fundamentals](chapter-01-understanding-performant-python-summary.md) — understand computation and data movement.
2. [Ch. 2: Profiling](chapter-02-profiling-to-find-bottlenecks-summary.md) — distinguish function time, line time, and memory use.
3. [Ch. 3: Lists/tuples](chapter-03-lists-and-tuples-summary.md) and [Ch. 4: Dicts/sets](chapter-04-dictionaries-and-sets-summary.md) — choose better algorithms and structures.
4. [Ch. 5: Generators](chapter-05-iterators-and-generators-summary.md) — avoid storing data unnecessarily.
5. [Ch. 12: RAM](chapter-12-using-less-ram-summary.md) — use compact representations before adding machines.

Then branch by bottleneck:

| Evidence | Next chapters | First experiment |
|---|---|---|
| Python numeric loop dominates | [6](chapter-06-matrix-and-vector-computation-summary.md), [8](chapter-08-compiling-to-c-summary.md) | NumPy expressions or a small Numba-compiled loop |
| DataFrame transformation dominates | [7](chapter-07-pandas-dask-polars-summary.md) | Filter/project early; compare vectorized or lazy expressions |
| Waiting on network/DB dominates | [9](chapter-09-async-io-summary.md) | Bounded async I/O using compatible clients |
| Independent Python CPU tasks dominate | [10](chapter-10-multiprocessing-summary.md) | Batched process-pool tasks; measure serialization overhead |
| One machine is still insufficient | [11](chapter-11-clusters-and-job-queues-summary.md) | Compare vertical scaling before distributing |

## Chapter Map

| Chapter | What to retain |
|---|---|
| [1 — Understanding performance](chapter-01-understanding-performant-python-summary.md) | Locality, interpreter overhead, and correct-before-fast development |
| [2 — Profiling](chapter-02-profiling-to-find-bottlenecks-summary.md) | Profile to locate work; benchmark separately to compare changes |
| [3 — Lists and tuples](chapter-03-lists-and-tuples-summary.md) | Indexed lookup, sorted search, resize overhead, fixed structure |
| [4 — Dictionaries and sets](chapter-04-dictionaries-and-sets-summary.md) | Average constant-time operations need sound hash/equality behavior |
| [5 — Iterators and generators](chapter-05-iterators-and-generators-summary.md) | Laziness reduces retained data, but not all state or computation |
| [6 — Matrix/vector computation](chapter-06-matrix-and-vector-computation-summary.md) | Typed buffers, vectorized work, reuse, and CPU/GPU transfer costs |
| [7 — Pandas, Dask, Polars](chapter-07-pandas-dask-polars-summary.md) | Column expressions, lazy optimization, partitioning, and dtype choice |
| [8 — Compiling](chapter-08-compiling-to-c-summary.md) | Compile hot loops, not necessarily the entire application |
| [9 — Async I/O](chapter-09-async-io-summary.md) | Overlap waits; bound concurrency and keep the loop responsive |
| [10 — Multiprocessing](chapter-10-multiprocessing-summary.md) | Account for startup, data transfer, shared memory, and random streams |
| [11 — Clusters/job queues](chapter-11-clusters-and-job-queues-summary.md) | Distributed systems add operational and delivery complexity |
| [12 — Less RAM](chapter-12-using-less-ram-summary.md) | Compact types and structures chosen for the questions you ask |
| [13 — Field lessons](chapter-13-lessons-from-the-field-summary.md) | Solving the right problem can eliminate the optimization entirely |

## Do Not Confuse

- **Big-O vs. measured time:** hash/equality costs, caches, allocation, and input sizes influence actual runtime.
- **Vectorized vs. zero-copy:** an array expression may execute native code but still allocate large intermediates.
- **Less precision vs. free speed:** narrower floats change numerical behavior. Check tolerance and stability, including GPU mixed precision.
- **Concurrency vs. parallelism:** async overlaps waits; it does not distribute Python CPU work across cores.
- **`fork` vs. copying:** inherited memory starts copy-on-write; task arguments may still be serialized. Explicit shared memory works differently.

## Practice (15–25 Minutes)

Compare repeated membership checks while including construction cost:

```python
from timeit import repeat

values = list(range(10_000))
queries = list(range(9_000, 10_000))
lookup = set(values)

def scan_list():
    return sum(q in values for q in queries)

def scan_set():
    return sum(q in lookup for q in queries)

def build_and_scan_set():
    lookup = set(values)
    return sum(q in lookup for q in queries)

assert scan_list() == scan_set() == build_and_scan_set() == 1000
for fn in (scan_list, scan_set, build_and_scan_set):
    print(fn.__name__, repeat(fn, number=1, repeat=3))
```

Repeat with one query instead of 1,000. Explain why a better lookup complexity may not justify constructing a new set for one lookup. Record Python version, input size, repeats, and whether setup was included; do not infer memory use from timing.

## Self-Check

1. Why should correctness tests run before and after an optimization?
2. When can threads accelerate CPU-heavy work on GIL-enabled CPython?
3. Which question needs a Bloom filter, and which needs HyperLogLog?
4. What can make more process workers slower?

**Answer cues:** preserve semantics; native code releases the GIL; approximate membership vs. unique count; transfer, contention, startup, oversubscription, RAM pressure.

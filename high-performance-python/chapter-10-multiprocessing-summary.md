# Chapter 10 Summary: The multiprocessing Module
*High Performance Python, 3rd Edition*

---

## Core Problem: Bypassing the GIL

Python's GIL prevents true CPU parallelism with threads — only one thread executes Python bytecode at a time. **Multiprocessing** solves this by spawning separate OS processes, each with its own Python interpreter and GIL. No GIL contention → true parallel CPU usage.

**Threads vs. Processes:**
- Threads: share memory, subject to GIL → no CPU speedup for CPU-bound code
- Processes: independent interpreters, no shared memory by default → near-linear CPU scaling

---

## Estimating Pi (Monte Carlo Benchmark)

Throwing 400M random darts; testing with 1, 2, 4, 8, 16 workers:

| Method | Workers | Runtime |
|---|---|---|
| Single process (baseline) | 1 | ~182 s |
| Threads | 8 | ~182 s (no speedup — GIL!) |
| Processes | 2 | ~92 s (2× speedup) |
| Processes | 4 | ~46 s (4× speedup) |
| Processes | 8 | ~24 s (8× speedup) |
| Processes | 16 (hyperthreads) | ~23 s (barely better than 8) |

> Hyperthreading adds little for CPU-bound Python work — hyperthreads share the same physical core's resources and aren't cache-friendly.

---

## `multiprocessing.Pool`

```python
from multiprocessing import Pool

# worker_function must be defined at module scope.
if __name__ == "__main__":
    with Pool(processes=4) as pool:
        results = pool.map(worker_function, list_of_args)
```

- `pool.map` distributes work across processes and collects results
- Each forked process costs ~10–20 MB of RAM; large data structures cost more
- Running out of RAM → swap → all parallelization benefit is lost

---

## Joblib — Easier Multiprocessing

Joblib wraps `multiprocessing` with a cleaner API and transparent caching:

```python
from joblib import Parallel, delayed

results = Parallel(n_jobs=8, verbose=1)(
    delayed(worker_fn)(arg) for arg in args
)
```

- Switch to serial for debugging with `n_jobs=1` — no code change needed
- Uses `cloudpickle` → works with interactively-defined functions
- Built on `Loky` (improved process pool)

### Joblib Disk Caching
```python
from joblib import Memory
memory = Memory("/tmp/cache", verbose=0)

@memory.cache
def expensive_fn(arg1, arg2):
    ...
```
- Caches results to disk based on function arguments
- Cache persists between sessions; refreshed if function code changes
- First call: 24 s; **second call: 0.5 s** (from cache)
- ⚠️ Warning: avoid passing large pickled objects (DataFrames, etc.) — pickling overhead can negate parallelism gains

---

## Random Numbers in Parallel

- Python's `random` module: automatically re-seeded in each forked process by `multiprocessing`
- NumPy RNGs inherited under `fork` can produce duplicate streams. Use `numpy.random.SeedSequence(seed).spawn(n_workers)` to derive independent, reproducible worker streams rather than giving every worker the same seed.
- Start methods vary: macOS uses `spawn` by default; Python 3.14 uses `forkserver` by default on supported POSIX systems. Do not assume workers inherit initialized globals; pass shared buffers through an initializer or attach to named `multiprocessing.shared_memory` blocks.
- For critical applications (medical/financial), research the statistical quality of parallel random streams

---

## NumPy + Multiprocessing

NumPy vectorized operations are **16× faster** than pure Python for the pi estimation:

```python
# numpy vectorized version
x = np.random.uniform(0, 1, nbr_estimates)
y = np.random.uniform(0, 1, nbr_estimates)
return np.sum(x*x + y*y <= 1.0)
```

NumPy releases the GIL for many operations → better hyperthread utilization (can see 70%+ on all CPUs).

---

## Sharing NumPy Arrays Between Processes

By default, `fork` initially shares inherited memory through **copy-on-write**; writes can create private copies. Under `spawn`/`forkserver`, passing arrays as task arguments generally serializes them unless explicit shared memory is used. Repeated transfer of a large array can dominate runtime.

### Solution: `multiprocessing.Array` + `numpy.frombuffer`

```python
import multiprocessing, ctypes, numpy as np

# Create shared memory block
shared_array_base = multiprocessing.Array(ctypes.c_double, SIZE_A * SIZE_B, lock=False)
# Wrap with numpy (no copy)
main_nparray = np.frombuffer(shared_array_base, dtype=ctypes.c_double)
main_nparray = main_nparray.reshape(SIZE_A, SIZE_B)

# Forked processes access the same memory
pool = multiprocessing.Pool(processes=8)
pool.map(worker_fn, range(SIZE_A))
```

- `lock=False`: explicit about bypassing the built-in lock (we manage access ourselves)
- Workers access the same explicitly shared buffer; matching `id()` values across processes do **not** prove sharing because each process has its own address space
- Ideal for read-heavy workloads or workloads with disjoint write regions per worker
- Be careful with concurrent writes — use locks if needed

---

## Synchronizing Shared State

### File Locking (slowest)
```python
@fasteners.interprocess_locked('/tmp/tmp_lock')
def work(filename, max_count):
    ...
```
- Without locking: 4 concurrent processes writing to the same file → data corruption
- `fasteners` module adds interprocess locking with a simple decorator

### `multiprocessing.Value` / `RawValue`
```python
value = multiprocessing.Value('i', 0)   # has built-in lock (but not atomic!)
lock = multiprocessing.Lock()

with lock:
    value.value += 1
```
- `Value` has a lock but doesn't provide **atomic increment** — still needs explicit `Lock`
- `RawValue` has no built-in lock → slightly faster with an explicit `Lock`
- Use `with lock:` context manager for cleaner code

---

## Finding Prime Numbers: Queues of Work

For tasks with variable computation time (like prime checking), use a **Queue** to distribute work dynamically:

```python
from multiprocessing import Process, Queue

def worker(inputs, outputs):
    while True:
        task = inputs.get()
        if task is None: break
        outputs.put(check_prime(task))
```

- Queue-based workers are better than fixed `map` partitions when task times vary
- Use **poison pills** (`None`) to signal workers to terminate

### Interprocess Communication (IPC) for Early Termination
For prime verification problems where multiple workers can find an answer (e.g., checking if a factor exists), workers need to signal each other to stop:

| IPC Method | Speed | Complexity |
|---|---|---|
| `manager.Value` (via Manager proxy) | Slowest | Low |
| Redis flag | Slow | Medium |
| `RawValue` + Lock | Fast | Low |
| `mmap` (memory-mapped file) | Fastest | Medium |

> **Lesson**: IPC adds significant complexity. Sometimes a **naive parallel solution** (no IPC, accept redundant work) is faster overall than a "smart" solution with expensive IPC.

---

## Key Takeaways

1. Threads don't help CPU-bound Python code — use `multiprocessing` or external tools
2. `pool.map` gives near-linear speedup up to the number of physical CPU cores
3. Hyperthreads give marginal gains for CPU-bound work
4. NumPy releases the GIL → better hyperthread utilization
5. Joblib is a drop-in improvement over `multiprocessing` with caching
6. Sharing large NumPy arrays: use `multiprocessing.Array` + `frombuffer` to avoid copies
7. Create independent NumPy random streams per worker; record seeds and worker assignment for reproducibility
8. IPC is powerful but complex — prefer simpler patterns unless forced otherwise
9. Running out of RAM from forked processes defeats all parallelism gains

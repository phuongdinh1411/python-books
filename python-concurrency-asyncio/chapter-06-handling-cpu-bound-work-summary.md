# Chapter 6 – Handling CPU-Bound Work

## Core Idea
asyncio is single-threaded — a CPU-intensive coroutine freezes every other task. Chapter 6 solves this with Python's `multiprocessing` module: distribute work across multiple OS processes to get true parallelism. It shows how to bridge the async world with process pools, build a MapReduce pipeline, and safely share state between processes with locks.

---

## The Problem: CPU-Bound Code Blocks the Loop

```python
async def main():
    task1 = asyncio.create_task(cpu_heavy())   # blocks the loop
    task2 = asyncio.create_task(delay(1))      # never runs while task1 is executing
    await asyncio.gather(task1, task2)
```

When `cpu_heavy()` runs it never yields, so `task2` is completely starved.

---

## `ProcessPoolExecutor` + `run_in_executor`

`loop.run_in_executor(pool, fn, *args)` offloads a regular (non-async) function to a pool and returns an awaitable. Use `concurrent.futures.ProcessPoolExecutor` for CPU-bound work.

```python
import asyncio
import concurrent.futures

def cpu_bound(n: int) -> int:
    return sum(i * i for i in range(n))

async def main():
    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        # runs in a separate process; awaitable in the event loop
        result = await loop.run_in_executor(pool, cpu_bound, 1_000_000)
    print(result)

asyncio.run(main())
```

`run_in_executor(None, fn)` uses the default **thread** pool. Pass an explicit `ProcessPoolExecutor` for CPU work.

### Running multiple CPU tasks concurrently
```python
with concurrent.futures.ProcessPoolExecutor() as pool:
    tasks = [
        loop.run_in_executor(pool, cpu_bound, n)
        for n in [500_000, 600_000, 700_000]
    ]
    results = await asyncio.gather(*tasks)
```

---

## MapReduce with asyncio and Multiprocessing

### The pattern
1. **Partition** the data into chunks.
2. **Map:** run `map_fn(chunk)` in parallel across processes.
3. **Reduce:** merge intermediate results into a final answer.

### Partitioning
```python
def partition(data: list, chunk_size: int):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]
```

### Full parallel MapReduce
```python
import functools

async def main(partition_size: int):
    with open('large_data_file') as f:
        contents = f.readlines()

    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        tasks = [
            loop.run_in_executor(pool, functools.partial(map_frequencies, chunk))
            for chunk in partition(contents, partition_size)
        ]
        intermediate = await asyncio.gather(*tasks)  # all maps run in parallel
        final = functools.reduce(merge_dicts, intermediate)

asyncio.run(main(partition_size=60_000))
```

**Performance (32-core AWS c5ad.8xlarge):**
- Serial version: ~76 seconds
- Parallel MapReduce: ~18 seconds  (~4× speedup)

### Choosing partition size
- **Too small:** pickling/unpickling overhead dominates.
- **Too large:** fewer chunks than CPU cores; cores sit idle.
- Rule of thumb: aim for `num_chunks ≈ num_cpu_cores × 2–4`. Benchmark to confirm.

---

## Shared State and Locks

By default, child processes have **separate memory**. To share a counter (e.g., for progress reporting), use `multiprocessing.Value` (a single shared value) or `multiprocessing.Array`.

### Race condition without a lock
```python
# Two processes both do: counter.value += 1
# Result is non-deterministic — read-modify-write is not atomic
```

### Using a `multiprocessing.Lock`
```python
from multiprocessing import Value, Lock

def map_with_progress(chunk, counter, lock):
    # do work...
    with lock:
        counter.value += 1   # atomic increment

async def main():
    counter = Value('i', 0)   # shared integer, init to 0
    lock = Lock()
    with ProcessPoolExecutor() as pool:
        tasks = [
            loop.run_in_executor(
                pool,
                functools.partial(map_with_progress, chunk, counter, lock)
            )
            for chunk in partition(data, chunk_size)
        ]
        await asyncio.gather(*tasks)
    print(f'Completed {counter.value} chunks')
```

**Design principle:** avoid shared state between processes whenever possible. If you need it, minimise the critical section and always protect it with a lock.

---

## `multiprocessing` vs. `threading` for CPU Work

| | Threading | Multiprocessing |
|---|---|---|
| GIL | Held per thread; no true parallelism for Python CPU code | One GIL per process; true parallelism |
| Memory | Shared (cheap) | Separate (copies via pickling) |
| Overhead | Low | Higher (process spawn + pickle) |
| Best for | I/O-bound blocking APIs | CPU-bound Python code |

---

## Key Takeaway
For CPU-bound work: offload to `ProcessPoolExecutor` via `loop.run_in_executor`. Use MapReduce to partition large datasets across all cores. Tune partition size by benchmarking — the right size balances pickle overhead against parallelism. Share state only when necessary, and always protect it with a `multiprocessing.Lock`.

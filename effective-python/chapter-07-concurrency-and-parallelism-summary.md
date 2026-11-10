# Chapter 7 – Concurrency and Parallelism

## Core Idea
**Concurrency** = multiple tasks making progress (possibly interleaved on one core). **Parallelism** = multiple tasks running simultaneously on multiple cores. Python's GIL limits true parallelism for CPU-bound work in threads, but provides excellent models for I/O concurrency. Choosing the right tool depends on whether your bottleneck is I/O or CPU.

## The Python GIL
This advice assumes **GIL-enabled CPython**. Optional free-threaded builds exist from Python 3.13; native libraries can also release the GIL. Check your interpreter and dependencies before choosing a model.

- CPython's Global Interpreter Lock (GIL) allows only one thread to execute Python bytecode at a time
- Threads are excellent for **I/O-bound** work (blocking I/O commonly releases the GIL)
- Threads generally provide **no CPU parallel speedup for Python bytecode** on these builds — use processes or GIL-releasing native code

## Items Summary

### Item 52: Use `subprocess` to Manage Child Processes
- `subprocess.run()` and `subprocess.Popen` launch external processes
- Child processes run truly in parallel (separate OS processes, no GIL)
- Use for CPU-heavy work implemented in other tools (ffmpeg, openssl, etc.)
  ```python
  import subprocess
  result = subprocess.run(["echo", "Hello"], capture_output=True, text=True)
  print(result.stdout)
  ```
- `Popen` for async control (poll, communicate, kill)
- Set `timeout=` to avoid hanging indefinitely

### Item 53: Use Threads for Blocking I/O, Avoid for Parallelism
- Threads are useful when your program blocks on I/O (network, disk, db)
- Multiple threads can wait on I/O simultaneously — the GIL is released during waits
- Use `threading.Thread` for spawning; avoid for CPU-bound tasks
  ```python
  threads = [threading.Thread(target=fetch_url, args=(url,)) for url in urls]
  for t in threads: t.start()
  for t in threads: t.join()
  ```
- Do not expect CPU speedup for pure Python on GIL-enabled CPython; native GIL-releasing work and free-threaded builds are exceptions

### Item 54: Use `Lock` to Prevent Data Races in Threads
- Shared mutable state across threads causes data races even in Python
  (read-modify-write is not atomic)
- Use `threading.Lock` to serialize access:
  ```python
  lock = threading.Lock()
  with lock:
      counter += 1
  ```
- Use `with lock:` (context manager) — ensures unlock even on exceptions
- Minimize the scope inside the lock to reduce contention

### Item 55: Use `Queue` to Coordinate Work Between Threads
- `queue.Queue` is the preferred way to pass work between producer and consumer threads:
  ```python
  from queue import Queue
  q = Queue(maxsize=100)  # backpressure

  # Producer
  q.put(item)

  # Consumer
  item = q.get()
  q.task_done()
  ```
- `Queue` handles all locking internally — no manual locks needed
- `q.join()` blocks until all items have been processed (`task_done()` called for each)
- Use `maxsize` to implement backpressure — prevents the producer from overwhelming the consumer

### Item 56: Know How to Recognize When Concurrency Is Necessary
- Concurrency is needed when tasks are independent and blocking (I/O fan-out)
- Signs you need concurrency: program spends most of its time waiting for external resources
- A sequential loop over I/O calls is often the bottleneck — fan them out with threads or coroutines

### Item 57: Avoid Creating New Thread Instances for On-demand Fan-out
- Spawning a `Thread` per request is expensive and doesn't scale
  - Threads have high startup cost and memory overhead
  - Hard to limit parallelism and apply backpressure
- Use `ThreadPoolExecutor` or `asyncio` instead

### Item 58: Understand How Using `Queue` for Concurrency Requires Refactoring
- Refactoring sequential code to use `Queue` pipeline requires restructuring into producers/consumers
- The refactoring adds complexity — weigh against gains
- Consider whether `asyncio` coroutines would be simpler for the same I/O workload

### Item 59: Consider `ThreadPoolExecutor` When Threads Are Necessary for Concurrency
- `concurrent.futures.ThreadPoolExecutor` manages a pool of reusable threads:
  ```python
  from concurrent.futures import ThreadPoolExecutor

  with ThreadPoolExecutor(max_workers=10) as executor:
      futures = [executor.submit(fetch_url, url) for url in urls]
      results = [f.result() for f in futures]
  ```
- Reuses threads (no spawn overhead per task)
- `Future.result()` propagates exceptions cleanly
- Good balance of simplicity and control for I/O-bound fan-out

### Item 60: Achieve Highly Concurrent I/O with Coroutines
- Python 3.5+ `async`/`await`: coroutines run on a single thread via an event loop
- No GIL concerns; no thread overhead; can handle thousands of concurrent I/O tasks
  ```python
  import asyncio

  async def fetch(url):
      async with aiohttp.ClientSession() as session:
          async with session.get(url) as resp:
              return await resp.text()

  async def main():
      results = await asyncio.gather(*(fetch(url) for url in urls))
  ```
- **Use `asyncio` for high-concurrency I/O** (web scraping, API calls, chat servers)

### Item 61: Know How to Port Threaded I/O to `asyncio`
- Strategy: replace blocking calls with `async`/`await` equivalents
- Replace `threading.Thread` → `asyncio.Task` / `asyncio.gather`
- Replace `queue.Queue` → `asyncio.Queue`
- Replace `threading.Lock` → `asyncio.Lock`
- Most popular I/O libraries have async equivalents: `aiohttp`, `aiofiles`, `asyncpg`

### Item 62: Mix Threads and Coroutines to Ease the Transition to `asyncio`
- Gradual migration: run `asyncio` coroutines in threads or threads in the event loop
- `asyncio.run_coroutine_threadsafe(coro, loop)` — call async code from a thread
- `loop.run_in_executor(None, blocking_fn)` — run blocking code in a thread pool from async code
- Use this bridge pattern to migrate large codebases incrementally

### Item 63: Avoid Blocking the `asyncio` Event Loop to Maximize Responsiveness
- The event loop is single-threaded — any blocking call blocks **all** coroutines
- Never call blocking I/O, CPU-heavy code, or `time.sleep()` in `async` functions
- Use `await asyncio.sleep(n)` instead of `time.sleep(n)`
- Offload CPU-bound Python work with an explicitly supplied `ProcessPoolExecutor`: `await loop.run_in_executor(process_pool, cpu_heavy_function)`. Passing `None` chooses a thread pool — useful for blocking I/O, not generally for Python CPU parallelism.

### Item 64: Consider `concurrent.futures` for True Parallelism
- `ProcessPoolExecutor` bypasses the GIL by running tasks in separate processes:
  ```python
  from concurrent.futures import ProcessPoolExecutor

  with ProcessPoolExecutor() as executor:
      results = list(executor.map(cpu_heavy, items))
  ```
- Use for CPU-bound work (image processing, number crunching, ML inference)
- Overhead: process startup + pickling data — benchmark task size, batching, and data transfer rather than using a fixed time threshold
- Define workers at module scope and launch the pool under `if __name__ == "__main__":` in scripts so spawn/forkserver-based execution can import safely
- `ThreadPoolExecutor` for I/O-bound; `ProcessPoolExecutor` for CPU-bound

## Concurrency Decision Guide
| Bottleneck | Best Tool |
|---|---|
| I/O, low concurrency | `threading.Thread` / `ThreadPoolExecutor` |
| I/O, high concurrency | `asyncio` coroutines |
| CPU-bound work | `ProcessPoolExecutor` / `subprocess` |
| External program | `subprocess` |

## Key Takeaways
- Threads don't help CPU-bound code — use `ProcessPoolExecutor` or `subprocess`
- Use `Queue` and `Lock` correctly to avoid data races
- Prefer `ThreadPoolExecutor` over raw `Thread` spawning
- Use `asyncio` for high-concurrency I/O workloads
- Never block the event loop; offload blocking work to an executor

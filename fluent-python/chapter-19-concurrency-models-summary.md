# Chapter 19 – Concurrency Models in Python

## Core Idea
Python has three main concurrency models — **threads**, **processes**, and **coroutines** — and the GIL makes their trade-offs different from other languages. Understanding when each model helps (and when it doesn't) is essential for writing performant concurrent programs.

## Jargon
- **Concurrency**: multiple tasks making progress (not necessarily simultaneously)
- **Parallelism**: multiple tasks literally running at the same instant (requires multiple CPUs)
- **Process**: OS-managed execution unit with isolated memory
- **Thread**: execution unit within a process, sharing memory
- **Coroutine**: user-space cooperative execution unit; explicitly yields control
- **GIL**: Global Interpreter Lock — prevents multiple Python threads from executing Python bytecode simultaneously in CPython

## Spinner Example: Three Models Side-by-Side
```python
# Thread spinner
import threading
spinner = threading.Thread(target=spin, args=('thinking!', done))
spinner.start()
result = slow_function()
done.set()   # signal spinner to stop

# Process spinner
import multiprocessing
spinner = multiprocessing.Process(target=spin, args=('thinking!', done))
spinner.start()
result = slow_function()
done.set()

# Coroutine spinner
async def supervisor():
    spinner = asyncio.create_task(spin('thinking!'))
    result = await slow_function()
    spinner.cancel()
    return result
```

## The Real Impact of the GIL
- **I/O-bound tasks**: threads work well — the GIL is released during I/O (file reads, network calls, etc.)
- **CPU-bound tasks**: threads do NOT help — the GIL prevents true parallel execution of Python code
- **CPU-bound with C extensions**: many extension libraries (NumPy, OpenSSL) release the GIL, enabling real parallelism

## Homegrown Process Pool for CPU-Bound Work
```python
import multiprocessing as mp

def check_prime(n):
    return n, is_prime(n)

with mp.Pool() as pool:
    results = pool.map(check_prime, numbers)
```
Processes have higher overhead (memory, startup) but bypass the GIL entirely.

## Python in the Multicore World

| Domain | Typical approach |
|---|---|
| System administration | Threads (mostly I/O-bound) |
| Data science | NumPy/SciPy release the GIL; Dask/Spark for distributed work |
| Web/mobile backend | ASGI/async for I/O concurrency; processes for CPU workers |
| WSGI servers | Multiple worker processes (Gunicorn, uWSGI) |
| Distributed tasks | Celery, RQ, Dramatiq |

## Concurrency vs Parallelism Summary

| | Threads | Processes | Coroutines |
|---|---|---|---|
| GIL workaround | No | Yes | No (single-threaded) |
| Best for | I/O-bound | CPU-bound | I/O-bound, high concurrency |
| Memory | Shared | Isolated | Shared |
| Overhead | Low | High | Very low |
| Communication | Shared state (lock required) | Queues, Pipes | `await`, queues |
| Failure isolation | None | Good | None |

## Closing Thoughts
The GIL is not a bug — it simplifies the CPython implementation and makes single-threaded Python faster. The trade-off is CPU-bound parallelism, which requires `multiprocessing` or C extensions that release the GIL. For I/O-bound concurrency (the dominant case in web services), threads or async coroutines both work, with coroutines scaling better at high concurrency due to lower overhead. Choose the model that matches your bottleneck.

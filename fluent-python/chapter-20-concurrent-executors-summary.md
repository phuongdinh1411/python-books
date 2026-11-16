# Chapter 20 – Concurrent Executors

## Core Idea
`concurrent.futures` provides a high-level, uniform API for running I/O-bound or CPU-bound tasks concurrently via **thread pools** or **process pools**, hiding most of the complexity of threads and processes behind a `Future` abstraction.

## The `Future` Object
A `Future` represents the eventual result of an asynchronous computation:
```python
from concurrent.futures import Future
f = Future()
f.done()      # False if not yet complete
f.result()    # blocks until result is available
f.cancel()    # attempt to cancel (if not started)
```
Futures are created by the framework (executors), not by user code directly.

## `Executor.submit` and `as_completed`
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def download(url):
    return httpx.get(url).content

urls = ['http://...', ...]

with ThreadPoolExecutor(max_workers=20) as executor:
    future_to_url = {executor.submit(download, url): url for url in urls}
    for future in as_completed(future_to_url):  # yields futures as they complete
        url = future_to_url[future]
        try:
            data = future.result()
        except Exception as exc:
            print(f'{url}: {exc}')
        else:
            process(data)
```
`as_completed` yields futures in **completion order** (not submission order).

## `Executor.map`
Simpler when order matters and you want results in submission order:
```python
with ThreadPoolExecutor() as executor:
    results = list(executor.map(download, urls))  # blocks; returns in order
```

## `ProcessPoolExecutor` for CPU-Bound Work
```python
from concurrent.futures import ProcessPoolExecutor

def is_prime(n):
    ...

with ProcessPoolExecutor() as executor:
    results = list(executor.map(is_prime, large_numbers))
```
`ProcessPoolExecutor` spawns worker processes; each has its own Python interpreter and GIL — enabling true parallelism for CPU-bound code.

## Downloading with Progress and Error Handling
Pattern for robust concurrent downloads:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import tqdm

def download_many(cc_list, base_url, verbose, concur_req):
    counter = Counter()
    with ThreadPoolExecutor(max_workers=concur_req) as executor:
        to_do_map = {executor.submit(download_one, cc, base_url, verbose): cc
                     for cc in sorted(cc_list)}
        done_iter = as_completed(to_do_map)
        if not verbose:
            done_iter = tqdm.tqdm(done_iter, total=len(cc_list))
        for future in done_iter:
            try:
                status = future.result()
            except httpx.HTTPStatusError as exc:
                error_msg = f'HTTP {exc.response.status_code}'
                status = DownloadStatus.ERROR
            except KeyboardInterrupt:
                break
            else:
                error_msg = ''
            counter[status] += 1
    return counter
```

## `ThreadPoolExecutor` vs `ProcessPoolExecutor`

| | `ThreadPoolExecutor` | `ProcessPoolExecutor` |
|---|---|---|
| Best for | I/O-bound (network, disk) | CPU-bound |
| GIL | Not bypassed | Bypassed |
| Memory | Shared | Isolated |
| Overhead | Low | Higher |
| Communication | Trivial | Must be picklable |
| Default workers | `min(32, cpu+4)` | `os.cpu_count()` |

## Where Are the Futures?
When using `executor.map`, futures are created internally and hidden. `executor.submit` exposes them, enabling `as_completed` patterns and per-result error handling. Use `submit` when you need fine-grained control; `map` when simplicity suffices.

## Closing Thoughts
`concurrent.futures` is the right starting point for concurrency in Python. It provides thread pools and process pools behind the same interface, making it easy to switch. The `Future` object, `submit`, and `as_completed` are the core API. For I/O-heavy workloads where concurrency needs to scale to thousands of connections, `asyncio` (Chapter 21) offers less overhead; but for dozens to hundreds of concurrent tasks, `ThreadPoolExecutor` is simpler and sufficient.

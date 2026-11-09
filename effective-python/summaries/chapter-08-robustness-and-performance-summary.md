# Chapter 8 – Robustness and Performance

## Core Idea
Once a Python program is functionally correct, the next step is making it **production-ready**: robust under unexpected conditions and performant with real-world data. Python provides built-in tools for both — but you must know which tool to reach for and when.

## Items Summary

### Item 65: Take Advantage of Each Block in `try/except/else/finally`
Each block has a distinct, non-overlapping purpose:

| Block | When it runs | Use for |
|---|---|---|
| `try` | Always | Code that might raise |
| `except` | On exception | Handle specific errors |
| `else` | Only if no exception was raised | Code that should run only on success |
| `finally` | Always, even after exception/return | Cleanup (close files, release locks) |

```python
def read_config(path):
    try:
        handle = open(path)
    except FileNotFoundError:
        return default_config()
    else:
        data = handle.read()  # runs only if open succeeded
        return parse(data)
    finally:
        handle.close()  # always runs
```
The `else` block is often overlooked but important: it prevents accidentally catching exceptions thrown by the *success* path code.

### Item 66: Consider `contextlib` and `with` Statements for Reusable `try/finally` Behavior
- The `with` statement encapsulates `try/finally` for resource management
- Make your own context managers with `contextlib.contextmanager`:
  ```python
  from contextlib import contextmanager

  @contextmanager
  def managed_resource():
      resource = acquire()
      try:
          yield resource
      finally:
          release(resource)

  with managed_resource() as r:
      use(r)
  ```
- Cleaner than subclassing `contextlib.AbstractContextManager`
- Also use `contextlib.ExitStack` to manage a variable number of context managers

### Item 67: Use `datetime` Instead of `time` for Local Clocks
- `time.localtime()` and `time.mktime()` depend on the OS timezone and have many edge cases
- `datetime` + `pytz` (or `zoneinfo` in Python 3.9+) is reliable and explicit:
  ```python
  from datetime import datetime
  import pytz

  eastern = pytz.timezone("US/Eastern")
  dt = datetime(2023, 6, 15, 12, 0, tzinfo=pytz.utc)
  dt_eastern = dt.astimezone(eastern)
  ```
- Always work in UTC internally; convert to local time only for display
- `zoneinfo` (Python 3.9+) is the modern stdlib alternative to `pytz`

### Item 68: Make `pickle` Reliable with `copyreg`
- `pickle` serializes Python objects but is fragile across code changes (class renames, field removals)
- Use `copyreg.pickle()` to register custom pickling functions:
  ```python
  import copyreg

  def pickle_game_state(state):
      kwargs = state.__dict__
      kwargs.setdefault("version", 2)  # add versioning
      return unpickle_game_state, (kwargs,)

  copyreg.pickle(GameState, pickle_game_state)
  ```
- Add version fields to pickle representations to handle schema evolution
- Consider alternatives (JSON, protobuf, msgpack) for cross-language or long-term storage

### Item 69: Use `decimal` When Precision Is Paramount
- Floating-point arithmetic has rounding errors: `0.1 + 0.2 != 0.3`
- `decimal.Decimal` provides exact decimal arithmetic:
  ```python
  from decimal import Decimal, ROUND_UP

  rate = Decimal("0.05")
  seconds = Decimal("5.5")
  cost = rate * seconds
  cost = cost.quantize(Decimal("0.01"), rounding=ROUND_UP)
  ```
- Use `Decimal` for: money, taxes, scientific measurements requiring precision
- Initialize from strings, not floats: `Decimal("0.1")` not `Decimal(0.1)`

### Item 70: Profile Before Optimizing
- Never guess where the bottleneck is — always measure first
- Use `cProfile` for accurate profiling:
  ```python
  import cProfile
  profiler = cProfile.Profile()
  profiler.runcall(my_function, *args)
  profiler.print_stats(sort="cumulative")
  ```
- Or from the command line: `python -m cProfile -s cumtime my_script.py`
- Focus on the top entries in `cumtime` (cumulative time) — those are your actual bottlenecks
- Profile **realistic workloads**, not microbenchmarks, to get actionable data

### Item 71: Prefer `deque` for Producer–Consumer Queues
- `list.pop(0)` is O(n) — shifts every remaining element
- `collections.deque` provides O(1) `append` and `popleft`:
  ```python
  from collections import deque
  q = deque()
  q.append(item)    # O(1)
  item = q.popleft()  # O(1)
  ```
- Always use `deque` for FIFO queues; use `list` for stacks (LIFO with `append`/`pop`)

### Item 72: Consider Searching Sorted Sequences with `bisect`
- `in` on a list is O(n); `bisect` uses binary search for O(log n) on sorted lists:
  ```python
  import bisect
  index = bisect.bisect_left(sorted_list, target)
  ```
- `bisect_left` / `bisect_right` find insertion points
- Use `insort` to maintain a sorted list efficiently
- Only use when data is already sorted and random access by index is needed

### Item 73: Know How to Use `heapq` for Priority Queues
- A **priority queue** always returns the smallest (or highest-priority) item first
- `heapq` provides an efficient min-heap in O(log n) push/pop:
  ```python
  import heapq

  heap = []
  heapq.heappush(heap, (priority, item))
  priority, item = heapq.heappop(heap)
  ```
- For a max-heap, negate priorities: `heappush(heap, (-priority, item))`
- Key operations: `heappush`, `heappop`, `heapify` (O(n) to turn a list into a heap), `nlargest`, `nsmallest`

### Item 74: Consider `memoryview` and `bytearray` for Zero-Copy Interactions with `bytes`
- `bytes` is immutable — any slice creates a new copy (expensive for large data)
- `memoryview` provides a zero-copy view into a buffer:
  ```python
  data = b"Hello World" * 1_000_000
  view = memoryview(data)
  chunk = view[1000:2000]  # no copy made
  ```
- `bytearray` is a mutable bytes buffer — combine with `memoryview` for efficient in-place editing
- Use for: network protocol parsing, video/audio processing, large binary data pipelines
- Reduces memory allocations and copies in high-throughput I/O code

## Key Takeaways
- Use `else` in `try/except` to separate success-path code from error handling
- Use `@contextmanager` for clean resource management
- Always work in UTC with `datetime`; use `zoneinfo`/`pytz` for timezone conversion
- Use `Decimal` for financial and precision arithmetic — never `float` for money
- Profile before optimizing — always measure, never guess
- Use `deque` for FIFO queues, `heapq` for priority queues, `bisect` for sorted search
- Use `memoryview` for zero-copy slicing of large binary data

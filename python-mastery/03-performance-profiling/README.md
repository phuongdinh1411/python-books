# Pillar 3 — Performance Profiling

> **Duration:** 1 week | **Priority:** 🟡 Medium-High

---

## 🎯 Learning Objectives

- Identify performance bottlenecks using CPU and memory profilers
- Read and interpret flame graphs
- Apply the profiling-first workflow (measure before optimizing)
- Use `py-spy` safely on production processes
- Write targeted micro-benchmarks with `timeit`
- Apply common optimization patterns (data structures, caching, generators)

---

## 📚 Resources

| Resource | Type | Free? |
|----------|------|-------|
| [Python Official Profiling docs](https://docs.python.org/3/library/profile.html) | 📄 Docs | ✅ Free |
| [tracemalloc docs](https://docs.python.org/3/library/tracemalloc.html) | 📄 Docs | ✅ Free |
| [py-spy — GitHub](https://github.com/benfred/py-spy) | 🛠️ Tool | ✅ Free |
| [Speedscope.app](https://www.speedscope.app/) | 🛠️ Tool | ✅ Free |
| [line_profiler — GitHub](https://github.com/pyutils/line_profiler) | 🛠️ Tool | ✅ Free |
| [Real Python: Python profiling](https://realpython.com/python-profiling/) | 📄 Article | ✅ Free |
| [Python Performance Tips — Official Wiki](https://wiki.python.org/moin/PythonSpeed/PerformanceTips) | 📄 Docs | ✅ Free |

> 💡 **Optional paid book:** *High Performance Python 2nd Ed* — Gorelick & Ozsvald (O'Reilly)

---

## The Golden Rule of Optimization

> **"Measure first, optimize second."**
> Never guess where the bottleneck is. Profile first, always.

The optimization workflow:
```
1. Write correct code
2. Profile → find the hot path
3. Optimize only the bottleneck
4. Re-profile to confirm improvement
5. Repeat
```

---

## Section 1 — `cProfile` and `pstats` (CPU Profiling)

### Basic `cProfile` Usage

```python
import cProfile
import pstats
import io

def slow_function():
    total = 0
    for i in range(1_000_000):
        total += i * i
    return total

def main():
    for _ in range(10):
        slow_function()

# Method 1: command line
# python -m cProfile -s cumulative my_script.py

# Method 2: programmatic
profiler = cProfile.Profile()
profiler.enable()
main()
profiler.disable()

# Print stats
stream = io.StringIO()
stats = pstats.Stats(profiler, stream=stream)
stats.strip_dirs()
stats.sort_stats("cumulative")   # sort by cumulative time
stats.print_stats(20)            # top 20 functions
print(stream.getvalue())
```

### Understanding `cProfile` Output

```
ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
    10    0.420    0.042    0.420    0.042  script.py:4(slow_function)

ncalls  — number of calls
tottime — time spent in this function (excluding sub-calls)
cumtime — total time including sub-calls ← use this for bottleneck finding
percall — average per call
```

### Save and Load Profiling Data

```python
import cProfile

profiler = cProfile.Profile()
profiler.enable()
main()
profiler.disable()

# Save for later analysis or visualization
profiler.dump_stats("/tmp/profile_output.prof")

# Load and analyze
import pstats
stats = pstats.Stats("/tmp/profile_output.prof")
stats.sort_stats("cumulative")
stats.print_callers("slow_function")   # who calls this?
stats.print_callees("main")            # what does main call?
```

---

## Section 2 — `line_profiler` (Line-by-Line CPU)

```bash
pip install line-profiler
```

```python
# Decorate the function you want to profile
from line_profiler import LineProfiler

def process_data(data: list) -> list:
    result = []
    for item in data:
        if item % 2 == 0:
            result.append(item * item)
        else:
            result.append(item + 1)
    return result

profiler = LineProfiler()
profiler.add_function(process_data)
profiler.enable_by_count()

data = list(range(1_000_000))
output = process_data(data)

profiler.disable_by_count()
profiler.print_stats()
```

Output:
```
Line #   Hits      Time   Per Hit   % Time  Line Contents
=======================================================
     3              1   1.5e+04  1.5e+04      0.3   result = []
     4    1000000   2.1e+07     21.0     46.1   for item in data:
     5    1000000   8.5e+06      8.5     18.6     if item % 2 == 0:
     6     500000   7.2e+06     14.4     15.8       result.append(...)
     ...
```

---

## Section 3 — `memory_profiler` and `tracemalloc`

### `memory_profiler`

```bash
pip install memory-profiler
```

```python
from memory_profiler import profile

@profile
def load_large_file(path: str) -> list:
    with open(path) as f:
        lines = f.readlines()       # loads all lines into memory at once
    data = [line.strip() for line in lines]
    return data

@profile
def stream_large_file(path: str):
    """Better: stream line by line."""
    for line in open(path):         # generator — constant memory!
        yield line.strip()

# Run: python -m memory_profiler script.py
```

Output shows MB used at each line.

### `tracemalloc` — Built-in Memory Tracing

```python
import tracemalloc

tracemalloc.start()

# Code to profile
data = {str(i): [j for j in range(100)] for i in range(1000)}
snapshot = tracemalloc.take_snapshot()

# Top 10 memory consumers
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)

# Find memory leaked between two snapshots
tracemalloc.start()
snapshot1 = tracemalloc.take_snapshot()

leaked = []
for _ in range(1000):
    leaked.append(list(range(1000)))   # intentional "leak"

snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, "lineno")
print("Top memory increases:")
for stat in top_stats[:5]:
    print(stat)
```

---

## Section 4 — `py-spy` (Production-Safe Sampling Profiler)

`py-spy` is a **sampling profiler** — it peeks at the Python stack periodically
without instrumenting your code. Zero production overhead.

```bash
pip install py-spy

# Profile a running process (by PID)
py-spy top --pid 12345

# Record a flame graph
py-spy record -o profile.svg -- python my_script.py

# Profile with subprocesses
py-spy record --subprocesses -o profile.svg -- python my_script.py
```

### Reading Flame Graphs

```
  ┌─────────────────────────────────────┐
  │            main()                   │  ← bottom: entry point
  ├──────────────────────┬──────────────┤
  │    process_items()   │  load_data() │  ← callees of main
  ├────────────────┬─────┤              │
  │  compute()     │ fmt │              │  ← wide = more time spent here
  └────────────────┴─────┴──────────────┘

Width = time proportion
Stack depth = call depth
Hover/click = exact percentages
```

Upload the `.svg` to https://www.speedscope.app/ for interactive exploration.

---

## Section 5 — `timeit` for Micro-Benchmarks

```python
import timeit

# Method 1: timeit.timeit
t = timeit.timeit(
    stmt='"-".join(str(n) for n in range(100))',
    number=100_000
)
print(f"Generator: {t:.4f}s")

t = timeit.timeit(
    stmt='"-".join([str(n) for n in range(100)])',
    number=100_000
)
print(f"List comp: {t:.4f}s")

# Method 2: command line
# python -m timeit '"-".join(str(n) for n in range(100))'

# Method 3: Comparison class
from timeit import Timer

setups = {
    "dict_literal": '{"a": 1, "b": 2}',
    "dict_constructor": 'dict(a=1, b=2)',
}
for name, stmt in setups.items():
    t = Timer(stmt)
    runs = t.repeat(repeat=5, number=100_000)
    print(f"{name}: min={min(runs):.4f}s, avg={sum(runs)/len(runs):.4f}s")
```

---

## Section 6 — Common Optimization Patterns

### 1. Use the Right Data Structure

```python
import timeit

# Membership check: list O(n) vs set O(1)
large_list = list(range(100_000))
large_set = set(range(100_000))

t_list = timeit.timeit(lambda: 99_999 in large_list, number=1000)
t_set = timeit.timeit(lambda: 99_999 in large_set, number=1000)

print(f"List: {t_list:.4f}s")   # ~1.5s
print(f"Set:  {t_set:.4f}s")    # ~0.0001s
```

### 2. Generators vs Lists (Memory)

```python
import sys

# List comprehension: creates entire list in memory
squares_list = [x ** 2 for x in range(1_000_000)]
print(sys.getsizeof(squares_list))   # ~8 MB

# Generator: computes on demand, O(1) memory
squares_gen = (x ** 2 for x in range(1_000_000))
print(sys.getsizeof(squares_gen))    # ~112 bytes!

# When to use generators: when you only iterate once
total = sum(x ** 2 for x in range(1_000_000))   # never materializes
```

### 3. `functools.lru_cache` for Memoization

```python
from functools import lru_cache
import timeit

def fib_slow(n: int) -> int:
    if n < 2:
        return n
    return fib_slow(n - 1) + fib_slow(n - 2)

@lru_cache(maxsize=None)
def fib_fast(n: int) -> int:
    if n < 2:
        return n
    return fib_fast(n - 1) + fib_fast(n - 2)

t_slow = timeit.timeit(lambda: fib_slow(30), number=10)
t_fast = timeit.timeit(lambda: fib_fast(30), number=10)
print(f"Slow: {t_slow:.4f}s")
print(f"Fast: {t_fast:.6f}s")   # thousands of times faster
```

### 4. Local Variable Lookups Are Faster

```python
import math, timeit

def with_global():
    total = 0
    for _ in range(1_000_000):
        total += math.sqrt(total + 1)   # global lookup each time
    return total

def with_local():
    total = 0
    sqrt = math.sqrt    # bind to local variable
    for _ in range(1_000_000):
        total += sqrt(total + 1)   # local lookup: faster
    return total
```

### 5. String Building

```python
# SLOW: string + string creates a new object each time
def build_slow(parts: list) -> str:
    result = ""
    for p in parts:
        result += p   # O(n^2) !
    return result

# FAST: join is O(n)
def build_fast(parts: list) -> str:
    return "".join(parts)
```

### 6. `__slots__` for Many Small Objects (see Pillar 1)

---

## 🏋️ Exercises

### Exercise 1 — Profile a Slow API Endpoint
Write a FastAPI route that processes a large dataset slowly. Profile it with `cProfile`
and `line_profiler`, find the bottleneck, and optimize it. Measure the speedup.

### Exercise 2 — Find a Memory Leak
Write code that leaks memory (e.g., appending to a module-level list in a loop).
Use `tracemalloc` to identify and fix the leak.

### Exercise 3 — Flame Graph Analysis
Run `py-spy record` on a script that does:
- JSON parsing of a large file
- Some computation
- Writing output

Analyze the flame graph and identify the top 3 time consumers.

### Exercise 4 — Benchmark Comparison
Compare these approaches for the same task (parsing 100k records):
- Using `csv.reader`
- Using `pandas`
- Using a custom generator

---

## ✅ Self-Check Questions

1. What is the difference between `tottime` and `cumtime` in cProfile output?
2. When would you use `line_profiler` over `cProfile`?
3. Why is `py-spy` safe to use in production?
4. What is a flame graph and how do you read it?
5. What is the time complexity difference between `list` and `set` membership checks?
6. Why are generators more memory-efficient than list comprehensions?
7. When does `lru_cache` cause problems?
8. What is the problem with `str1 + str2` in a loop?

---

## 🔗 Key Links

- https://github.com/benfred/py-spy
- https://www.speedscope.app/
- https://docs.python.org/3/library/profile.html
- https://docs.python.org/3/library/tracemalloc.html
- https://github.com/pyutils/line_profiler

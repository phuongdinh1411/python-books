# Chapter 2 Summary: Profiling to Find Bottlenecks
*High Performance Python, 3rd Edition*

---

## Core Philosophy

> **Never optimize without profiling first. Form a hypothesis, then measure.**

"Always be driven by results that you have measured." Profiling inevitably slows code, but the insights are invaluable. The goal is to identify where time is actually spent — not where you *think* it is spent.

---

## Benchmark: The Julia Set

The chapter uses a **Julia set** calculation as its running example — a CPU-bound 1,000×1,000 pixel computation with a tight inner `while` loop. It's a realistic stand-in for scientific number-crunching workloads.

---

## Profiling Tools (from coarse to fine)

### 1. `print` + Decorator Timing
Simplest approach — wrap a function with `time.time()` before and after.
```python
def timefn(fn):
    @wraps(fn)
    def measure_time(*args, **kwargs):
        t1 = time.time()
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} took {time.time()-t1:.2f}s")
        return result
    return measure_time
```
Fast to add, but clutters output. Use the `timeit` module for micro-benchmarks.

### 2. Unix `time` Command
```bash
/usr/bin/time -p python script.py
/usr/bin/time --verbose python script.py  # includes max RSS, page faults
```
Reports `real`, `user`, `sys` times and **Maximum resident set size** (peak RAM). No code changes required.

### 3. `cProfile` — Function-Level Profiling
```bash
python -m cProfile -s cumulative script.py
python -m cProfile -o profile.stats script.py
```
Key columns: `ncalls`, `tottime` (time in function, excluding callees), `cumtime` (inclusive time).

- Adds significant overhead (~2× slowdown), but gives a full call tree
- Use `pstats` to load, sort, and print callers/callees programmatically
- **SnakeViz** (`pip install snakeviz`) visualizes the output as a zoomable diagram

### 4. `line_profiler` — Line-by-Line CPU Profiling
```bash
pip install line_profiler
kernprof -l -v script.py
```
Mark functions with `@profile`. Reports `% Time` per line.

Julia set findings:
- `while abs(z) < 2 and n < maxiter:` → **44% of total time** (the hottest line)
- `z = z * z + c` → 29%
- `n += 1` → 22%

> Tip: **Print and annotate the output** as you iterate; keep a record of changes. Use representative data.

### 5. `memory_profiler` — Line-by-Line RAM Profiling
```bash
pip install memory_profiler psutil
python -m memory_profiler script.py
mprof run script.py && mprof plot
```
Mark functions with `@profile`. Reports RAM per line (via `Mem usage` column).

- Runs 10–100× slower than normal
- Use `%memit` in Jupyter/IPython for quick checks
- Use `--pdb-mmem=XXX` to drop into pdb when RAM exceeds a threshold

Julia set finding: removing two pre-built lists (`zs`, `cs`) cut peak RAM from **140 MB → 60 MB**.

### 6. Scalene — Combined CPU + RAM + GPU Profiling
```bash
pip install scalene
scalene script.py
```
- No code changes needed (or add `@profile` for targeted profiling)
- Distinguishes **Python time** vs **native (C) time** vs **system time**
- Very low overhead compared to `line_profiler` + `memory_profiler`
- Has `%%scalene` magic for Jupyter cells
- Can suggest optimizations via ChatGPT API (be skeptical)

### 7. PySpy — Zero-Intrusion Sampling Profiler
```bash
pip install py-spy
py-spy top --pid <PID>
py-spy record -o profile.svg -- python script.py
```
- Attaches to a **running process** — no code changes, no restart needed
- Very useful for production systems and web servers
- Generates flame charts; supports subprocess profiling

### 8. VizTracer — Interactive Time-Based Call Stack
```bash
pip install viztracer
viztracer script.py && vizviewer results.json
```
- Left-to-right timeline of all function calls with zoom/click interactivity
- Tracks arguments, return values, and time per call
- Useful for diagnosing Pandas internals, deep call stacks, and concurrent code

---

## Bytecode Inspection

### `dis` Module
```python
import dis
dis.dis(some_function)
```
Shows the stack-based CPython bytecode. More bytecode lines → more overhead.

Key insight: `fn_terse` (using `sum(range(n))`) runs **2.7× faster** than `fn_expressive` (manual loop) because it calls an optimized C function with only 6 bytecode instructions vs. 17.

### Specialist (Python 3.11+)
```bash
pip install specialist
specialist script.py
```
Color-codes bytecode "specializations" — green means the interpreter has found stable types and is running fast. Helps spot where dynamic typing is hurting performance.

---

## Unit Testing During Optimization

Always maintain a test suite while profiling. **Never optimize with tests disabled.**

### No-op `@profile` Decorator
Add this to prevent `NameError` when running tests without `line_profiler`/`memory_profiler`:
```python
if 'line_profiler' not in dir() and 'profile' not in dir():
    def profile(func):
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        return inner
```

---

## Profiling Best Practices

- **Form a hypothesis before profiling** — verifies your intuition and helps you learn
- Isolate the code under test from the larger project
- Use representative data
- Disable CPU accelerators (Turbo Boost, SpeedStep) for stable benchmarks
- Run experiments many times; use AC power, not battery
- Use source control — branch before optimizing
- Profile **before and after** every change to confirm the optimization worked
- Check that your test suite covers all code paths being benchmarked (`coverage.py`)

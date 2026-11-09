# Chapter 7 Summary: Pandas, Dask, and Polars
*High Performance Python, 3rd Edition*

---

## Overview

This chapter covers three DataFrame libraries for tabular data:
- **Pandas** — the dominant, feature-rich standard; uses NumPy (and optionally Arrow) as its backend
- **Dask** — extends Pandas to larger-than-RAM datasets and multi-core/cluster parallelism
- **Polars** — a newer, faster alternative with a cleaner API and built-in query optimizer

---

## Pandas

### Internal Data Model
- Numeric columns are backed by **NumPy arrays** (contiguous memory → fast)
- String columns store **Python strings scattered in memory** (fragmented → slow)
- Pandas 2.x introduced **PyArrow** as an optional backend:
  - Arrow strings: compressed, much less RAM than NumPy object columns
  - Arrow integers: NaN-aware without converting to float
  - Best practice: use NumPy for numerics, Arrow for strings

### NaN / Missing Data Gotcha
- `numpy.float64` is naturally NaN-aware
- `numpy.int64` and `bool` are **not** NaN-aware → Pandas silently promotes to float64 when NaN is introduced (losing precision)
- Use Pandas's nullable `Int64` (capital I) or `boolean` types to avoid this

---

## Applying Functions to Rows: OLS Case Study

The chapter benchmarks several ways to apply an Ordinary Least Squares (OLS) calculation to 100,000 rows of a DataFrame.

### Which OLS Implementation Is Faster?
| Method | Time per call |
|---|---|
| `sklearn.LinearRegression.fit` | 0.515 µs |
| `numpy.linalg.lstsq` (direct) | **0.072 µs (7× faster)** |

Why? `scikit-learn` spends **85%** of its execution on:
1. `_validate_data` — checks for NaN, Inf, wrong shapes, etc.
2. `_preprocess_data` — offsets data to mean=0 for numerical stability

> These checks are valuable for developer safety, but you pay a performance tax. Only skip them if you're confident your data is already clean and correct.

### Row Iteration Methods (100,000 rows)

| Method | Time |
|---|---|
| `df.iloc[row_idx]` in loop | 7.3 s |
| `df.iterrows()` | 7.9 s |
| `df.apply(func, axis=1)` | 3.9 s |
| `df.apply(func, axis=1, raw=True)` | **3.1 s** |
| `df.apply(func, axis=1, raw=True, engine="numba")` | **0.40 s** |
| `df.apply(func, axis=1, raw=True, engine="numba", parallel=True)` | **0.13 s** |

- `raw=True` avoids creating an intermediate `Series` object per row (passes raw NumPy array directly)
- `engine="numba"` JIT-compiles the function — requires NumPy arrays, not PyArrow
- `parallel=True` spreads across CPU cores via Numba's auto-parallelizer
- **Total speedup from worst to best: ~56× (7.3s → 0.13s)**

### Anti-Pattern: Iterative Concatenation
```python
# BAD — each concat creates a new full copy of the growing Series
for ...:
    results = pd.concat((results, pd.Series([m])))   # 14 seconds!

# GOOD — build a list, construct once at the end
ms = []
for ...:
    ms.append(m)
results = pd.Series(ms)                              # 7 seconds
```
Each `concat` allocates a bigger object and copies everything. **Always accumulate into a Python list, then construct the DataFrame/Series once.**

### String Operations: `str` Accessor vs. `apply`
```python
# str accessor (3× slower): creates multiple intermediate Series
df['col'].str.split('.', expand=True)[1].str.find('9')   # 146 ms

# apply (3× faster): one pass, no intermediate objects
df['col'].apply(find_9)                                   # 52 ms
```

---

## Pandas Best Practices

- Install optional performance deps: `numexpr` and `bottleneck`
- Filter data *before* computing, not after — avoid unnecessary work
- Rename columns after transformations to maintain clarity
- Drop unused columns to reduce memory bloat
- Convert low-cardinality string columns to `category` dtype for faster `groupby`/`value_counts`
- Downcast numeric types (`float64` → `float16`, `int64` → `int8`) to save RAM when full range isn't needed
- Never use `inplace=True` — it's being deprecated
- **Always write unit tests** comparing optimized vs. safe implementations

---

## Dask

Dask extends Pandas to handle:
- **Larger-than-RAM datasets** — splits DataFrames into partitions by row
- **Multi-core and cluster parallelism** — using a lazy task graph

### Key Collections
| Collection | Use Case |
|---|---|
| `bag` | Unstructured data (JSON, text, Python objects) |
| `array` | Distributed NumPy operations |
| `dataframe` | Distributed Pandas operations |
| `delayed` | Lazy execution of arbitrary Python function chains |
| `future` | Immediate (non-lazy) task execution |

### Parallelizing Pandas with Dask
```python
import dask.dataframe as dd
ddf = dd.from_pandas(df, npartitions=8, sort=False)
results = ddf.apply(ols_lstsq_raw, axis=1, meta=(None, 'float64'), raw=True)\
             .compute(scheduler="processes")
```
- Rule of thumb: use **at least as many partitions as CPU cores**
- Use `scheduler="processes"` for CPU-bound tasks (avoids GIL)
- **dask-expr** (added 2024): automatic query optimization, similar to SQL predicate/projection pushdown — reduces developer tuning burden

### Diagnostics
Dask provides a rich dashboard showing:
- Bytes stored per worker (RAM pressure)
- Live task stream per worker
- Task occupancy breakdown
- Overall progress (Gantt-chart style)

### Swifter (auto-parallelize `apply`)
```python
import swifter
results = df.swifter.progress_bar(False).apply(ols_lstsq_raw, axis=1, raw=True)
```
Swifter samples your DataFrame, tries vectorization, then falls back to Dask multiprocessing. **One line of code**, no partitioning decisions needed.

---

## Polars

A newer, rapidly evolving competitor to Pandas with clear advantages:

| Feature | Pandas | Polars |
|---|---|---|
| API clarity | Multiple ways to solve each problem | Cleaner, more opinionated |
| Backend | NumPy + Arrow (mixed) | Arrow only (consistent) |
| Query optimizer | None built-in | **Built-in, automatic** |
| Execution | Eager only | Both eager and lazy |
| Speed | Baseline | **2–10× faster** for equivalent code |

### Key Advantages
- **Arrow-only backend**: no dual-path code, simpler internals
- **Automatic parallelization**: the query optimizer handles multi-core use transparently
- **Lazy mode + streaming**: can process larger-than-RAM data, similar to Dask, without manual partitioning
- Consistently faster in benchmarks — especially for operations involving strings or mixed types

### Caveat
- Still young → fewer public examples and GenAI training data
- Streaming mode (larger-than-RAM) is experimental
- "All benchmarks tell someone else's story" — run your own on your data

---

## Key Takeaways

1. `apply` with `raw=True` + Numba parallelized is the fastest Pandas row-wise approach (~56× faster than naive `iloc`)
2. **Never iteratively concatenate** Series/DataFrames — always build lists and construct once
3. PyArrow backend excels for string columns; NumPy is fine for numerics
4. Dask enables multi-core and cluster scaling with minimal code changes; dask-expr adds automatic optimization
5. Swifter is a one-line easy win worth trying before manually tuning Dask
6. Polars is 2–10× faster than Pandas for equivalent code and is worth adopting for new projects
7. Safety checks in libraries like scikit-learn have a real performance cost — know when you can safely bypass them

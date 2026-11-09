# Chapter 6 Summary: Matrix and Vector Computation
*High Performance Python, 3rd Edition*

---

## Core Problem: 2D Diffusion Equation

The chapter uses a **2D heat/diffusion simulation** as its benchmark problem throughout. Each grid cell is updated from its four neighbors each iteration — an inherently vectorizable operation. This drives all comparisons between pure Python, NumPy, and GPU code.

---

## Why Pure Python Lists Are Slow for Numerical Work

### Two Root Causes

**1. Memory Fragmentation**
Python lists store *pointers* to objects, not the objects themselves. Grid data is scattered across RAM. To read `grid[5][2]` requires **two pointer dereferences** before reaching actual data. This means:
- Data is not contiguous in memory
- The CPU cannot move it in one block transfer
- CPU caches are underutilized → more cache misses

**2. No Vectorization**
Python's interpreter cannot detect when a `for` loop is doing uniform arithmetic and issue SIMD/vector CPU instructions. Every element is processed one at a time.

### Profiling with `perf`
Linux's `perf stat` reveals what's really happening at the CPU level:

| Metric | What It Tells You |
|---|---|
| `instructions` | Total CPU instructions issued |
| `cycles` | CPU cycles used (compare to instructions for pipeline efficiency) |
| `cache-references` | Times the CPU looked in cache |
| `cache-misses` | Times data wasn't in cache (required slow RAM fetch) |
| `branches` | How many conditional branches in the code |
| `branch-misses` | Branch prediction failures (pipeline disruption) |
| `cs` (context switches) | Program interrupted by OS |
| `page-faults` | First memory access triggers OS to actually allocate |

---

## Key Optimization 1: Eliminate Redundant Memory Allocation

Pure Python version allocates a fresh `new_grid` list on **every iteration** of the simulation loop:
```python
new_grid = [[0.0] * ymax for _ in range(xmax)]  # 58ms per call!
```

Fix: allocate once upfront and **swap references**:
```python
evolve(grid, 0.1, next_grid)
grid, next_grid = next_grid, grid   # O(1) swap, no copy
```

Result: **~16% speedup** from this single change.

> **General rule**: Allocating memory involves kernel calls and cache-clearing. Move allocations outside hot loops whenever possible.

---

## Key Optimization 2: NumPy for Contiguous Memory + Vectorization

NumPy arrays store data in **contiguous blocks of memory** with a fixed type, enabling:
- Single-block data transfers to CPU cache
- Automatic use of SIMD/vector CPU instructions via C/Fortran backends
- Array-level arithmetic instead of element-by-element loops

### Norm-squared benchmark
| Method | Time |
|---|---|
| Pure Python loop | 48.3 ms |
| List comprehension + sum | 44.8 ms |
| `array` module loop | 66.4 ms (slower!) |
| **NumPy vectorized** | **999 µs (48× faster)** |

> The `array` module stores data contiguously but still requires Python to unbox each element on access — no free lunch without vectorization.

---

## Key Optimization 3: In-Place Operations and Memory Layout

NumPy operations like `a + b` create **new arrays** (memory allocation). Use in-place operations:
```python
out[:] = grid           # in-place copy
out *= D * dt           # in-place multiply
out += grid             # in-place add
```

Also use `numpy.roll` for periodic boundary conditions to avoid manual indexing.

### Memory allocation with `memit`
Track allocations during a function call to understand hidden costs.

---

## Key Optimization 4: `numexpr` — Fast In-Place Expressions

`numexpr` evaluates complex numpy expressions in chunks that fit in CPU cache, avoiding large intermediate arrays:
```python
numexpr.evaluate("D * (grid_xx + grid_yy) * dt + grid", out=out)
```

Benefits depend on grid size — best for medium-sized grids where cache efficiency matters most.

---

## Key Optimization 5: GPUs with PyTorch

### Why GPUs?
- Modern GPUs have **thousands of compute cores** (e.g., 4,362 on an RTX 2080 Ti)
- Designed for parallel floating-point operations
- Excellent for matrix math, Fourier transforms, convolutions

### Basic PyTorch GPU workflow
```python
grid = grid.to(device='cuda')     # copy to GPU memory
out = evolve(grid, dt)            # compute on GPU
```

### Critical performance gotcha: data transfer
Every `.cpu()`, `.numpy()`, or `.items()` call on a GPU tensor **copies data back to RAM** — very expensive!
- Adding one `grid.cpu()` per loop step caused a **2.54× slowdown** on a 2048×2048 grid

### GPU-Specific Operations: Convolutions
The Laplacian operation can be expressed as a **2D convolution**:
```python
kernel = [[0, -1, 0], [-1, 4, -1], [0, -1, 0]]
conv = torch.nn.Conv2d(..., padding_mode='circular', ...)
```
GPUs have specialized hardware for convolutions → 4× additional speedup on large grids.

### Numerical Precision on GPUs
| Precision | CPU (numpy) | GPU (PyTorch) |
|---|---|---|
| float64 | 40.3 ms | 1.24 ms |
| float32 | 20.2 ms | 623 µs |
| float16 | 256 ms (slow!) | **314 µs** |

CPU cannot use 16-bit float instructions efficiently; GPU excels at them.
Lower precision → faster compute and more data fits per cache line.

**Automatic Mixed Precision (AMP)**: `torch.amp.autocast` automatically selects the best precision per operation without sacrificing accuracy.

---

## Benchmarking Summary (all methods, 1000 iterations)

| Method | 512×512 | 2048×2048 | Speedup vs. Python |
|---|---|---|---|
| Pure Python | 4,580 s | 18,513 s | 1× |
| Python + memory reuse | 3,950 s | 16,582 s | 1.16× |
| NumPy | 53 s | 206 s | ~87× |
| NumPy + in-place + optimized Laplacian | 36 s | 149 s | ~126× |
| NumPy + numexpr | 34 s | 135 s | ~137× |
| **PyTorch (GPU)** | **0.91 s** | **3.57 s** | **~5,035×** |
| **PyTorch + convolution** | **0.24 s** | **0.94 s** | **~19,034×** |

---

## When to Use GPUs

✅ Good fit:
- Matrix/vector math (multiply, add, Fourier transforms)
- Code expressible as numpy operations (→ vectorizes well)
- Long stretches of GPU computation before needing results on CPU
- Deep learning training and inference

❌ Poor fit:
- Highly branching code (each step depends on previous result)
- Data larger than GPU RAM (typically 12–24 GB)
- Frequent CPU↔GPU data transfers

---

## Cautionary Tale: Verify Optimizations

Using `scipy.ndimage.filters.laplace` *looked* like an easy win — simpler code, wrapping condition handled automatically. But benchmarking showed:
- **No speedup vs. custom NumPy code**
- For large grids, actually **slower** (more instructions, more branches)

`perf` revealed the scipy code issued **2× more CPU instructions** due to its general-purpose boundary condition handling.

> **Always profile before and after any "optimization."** Form a hypothesis, then verify it with data.

---

## Key Takeaways

1. Memory fragmentation kills performance — contiguous data enables vectorization and cache efficiency
2. Eliminate allocations inside hot loops — allocate once, reuse with in-place operations
3. NumPy gives ~100× speedup over pure Python for numerical work
4. GPUs give ~5,000–20,000× speedup for this type of problem — but data transfer is the hidden cost
5. Lower numerical precision (float32, float16) gives free speedups on GPU
6. Convolutions are a GPU-optimized primitive — reformulate problems as convolutions when possible
7. Specialized code beats general-purpose library code — profile to verify

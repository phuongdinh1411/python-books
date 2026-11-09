# Chapter 8 Summary: Compiling to C
*High Performance Python, 3rd Edition*

---

## Why Compile?

Python's dynamic type system and the overhead of the CPython virtual machine mean every operation involves type lookups, reference counting, and interpreter dispatch. Compiling pushes numeric work down to C/machine code, eliminating this overhead.

**Key speedup example** (Julia set, 1M pixels, 300 max iterations):

| Method | Runtime | Speedup |
|---|---|---|
| CPython (pure Python) | 5.80 s | 1× |
| Cython (unannotated) | 4.2 s | ~1.4× |
| Cython + type annotations | 0.43 s | **13×** |
| Cython + expanded math | 0.23 s | **26×** |
| Cython + numpy + expanded math | 0.20 s | **29×** |
| Cython + OpenMP (8 cores) | 0.03 s | **193×** |
| Numba (2nd run) | 0.19 s | ~30× |
| Numba + OpenMP | 0.05 s | **116×** |
| PyPy (pure Python, expanded math) | 0.20 s | **29×** |

---

## JIT vs. AOT Compilers

- **AOT (Ahead-of-Time)**: Compile before running (Cython). Requires a build step but produces maximally optimized code.
- **JIT (Just-in-Time)**: Compile at runtime when hot spots are detected (Numba, PyPy). First run is slower due to compilation; subsequent runs are fast.

---

## Cython

Cython compiles annotated `.pyx` Python files into C code, then compiles that with a C compiler.

### Workflow
1. Write `.pyx` file (Python with optional C type annotations)
2. Build with `setup.py` using `cythonize()`
3. Import and use like a regular Python module

Or use **`pyximport`** to skip `setup.py` for simple cases:
```python
import pyximport; pyximport.install()
import cythonfn
```

### Cython Annotations (`cython -a file.pyx`)
Generates an HTML file where **darker yellow lines = more calls back into Python VM**.
- Focus on lines inside tight inner loops
- Lines outside loops rarely matter even if shaded

### Type Annotations
```python
cdef unsigned int i, n
cdef double complex z, c
```
- Declaring C types for variables inside loops eliminates Python VM calls
- **13× speedup** from adding a few `cdef` lines

### Strength Reduction
Replace expensive operations with mathematically equivalent cheaper ones:
```python
# Instead of abs(z) < 2  (involves sqrt)
z.real * z.real + z.imag * z.imag < 4   # no sqrt needed
```
→ additional **2× speedup**

### Cython + NumPy (Memoryview)
```python
def calculate_z(int maxiter, double complex[:] zs, double complex[:] cs):
```
- `double complex[:]` declares a 1D buffer-protocol array (works with numpy arrays)
- Avoids Python-level dereferencing per element → slightly faster than pure Python lists

### OpenMP Parallelization
```python
from cython.parallel import prange
with nogil:
    for i in prange(length, schedule="guided"):
        ...
```
- `with nogil:` disables the GIL — **do not access Python objects inside this block**
- `schedule="guided"` dynamically assigns work chunks for better load balancing
- Must add `-fopenmp` compiler/linker flags to `setup.py`
- Result: ~0.03 s (Cython + numpy + OpenMP = **193× speedup**)

---

## Numba

Numba is a JIT compiler using LLVM; works best on NumPy-heavy numeric code.

```python
from numba import jit

@jit
def calculate_z(maxiter, zs, cs, output):
    ...
```

- First run includes compilation time (~0.89 s); **second run: 0.39 s** (no recompilation if types unchanged)
- Inspect inferred types: `calculate_z.inspect_types()`
- Add parallelism with `@jit(parallel=True)` and `prange`

**Numba vs Cython:**
- Numba: less code, no compilation step, similar speed — best first choice for numpy code
- Cython: more control, supports external C libraries, more mature — best for complex cases

---

## PyPy

PyPy is a drop-in CPython replacement with a tracing JIT compiler.

- Pure Python Julia demo: CPython 5.8 s → PyPy **0.9 s** (no code changes!)
- With expanded math: PyPy **0.2 s** (matches Cython)
- Supports all built-in modules including `multiprocessing`
- Lags behind CPython version support (Python 3.12 → PyPy supports 3.10)
- NumPy with PyPy is **~6× slower** due to CPython extension overhead (HPy aims to fix this)
- May use more RAM than CPython

### Garbage Collector Difference
PyPy uses **mark-and-sweep** GC (not reference counting). Objects may be freed later.
- Files opened without explicit `close()` may not flush immediately
- Solution: always use `with open(...) as f:` context managers

---

## Foreign Function Interfaces (FFI)

When you need custom C/Fortran code, Python offers several FFI options:

### `ctypes` (built-in)
```python
import ctypes
lib = ctypes.CDLL("mylib.so")
lib.my_func.argtypes = [ctypes.c_double, ...]
lib.my_func.restype = None
```
- Tedious: manual type declarations and casts
- Can silently fail if types are wrong
- Good for simple, one-off integrations

### `cffi`
```python
from cffi import FFI
ffi = FFI()
ffi.cdef("void evolve(double **in, double **out, double D, double dt);")
lib = ffi.dlopen("diffusion.so")
```
- Simpler: just paste the C function signature
- Supports inline C code via `ffi.verify()`
- Better for evolving libraries

### `f2py` (NumPy)
- Wraps Fortran code into Python/NumPy
- Auto-generates the wrapper from Fortran source

### CPython C Extensions
- Full control, maximum performance
- Required boilerplate: `PyObject*`, `PyArg_ParseTuple`, `Py_BuildValue`, etc.
- Most direct way to write high-performance custom extensions

### Rust via PyO3
- Modern alternative to C extensions
- Memory-safe, excellent tooling (`maturin` for building)
- Growing community; good option for new custom extensions

---

## When to Use Each Technology

| Technology | Best For |
|---|---|
| **Numba** | NumPy-heavy numeric loops; minimal effort, fast payoff |
| **Cython** | Full control; calling C libraries; mature, production code |
| **PyPy** | Pure Python code with no heavy NumPy; drop-in replacement |
| **ctypes** | Quick wrapping of existing C `.so` files |
| **cffi** | Cleaner C library wrapping; inline C support |
| **Rust/PyO3** | New extensions needing memory safety + performance |

> **Rule**: Always handwrite C assumptions with benchmarks. Compiler-generated C (Cython) can match handwritten C — don't assume manual C is faster until measured.

# Chapter 4 – Comprehensions and Generators

## Core Idea
**Comprehensions** provide concise, readable syntax for deriving new collections from iterables. **Generators** extend this to streaming: producing values lazily, one at a time, with minimal memory footprint. Together they are among Python's most powerful features — but they have pitfalls when misused.

## Items Summary

### Item 27: Use Comprehensions Instead of `map` and `filter`
- List comprehension vs. `map`+`lambda`:
  ```python
  squares = [x**2 for x in a]                    # clear
  squares = list(map(lambda x: x**2, a))          # noisy
  ```
- Filtering inline:
  ```python
  even_squares = [x**2 for x in a if x % 2 == 0]  # clear
  ```
- Dict and set comprehensions work the same way:
  ```python
  {k: v for k, v in pairs}
  {x for x in items if x > 0}
  ```
- Prefer comprehensions over `map`/`filter` except for very simple cases with named functions

### Item 28: Avoid More Than Two Control Subexpressions in Comprehensions
- Nested comprehensions can get complex fast:
  ```python
  # OK: two levels
  flat = [x for row in matrix for x in row]

  # BAD: three levels — use a regular loop instead
  filtered = [x for sublist in matrix for row in sublist for x in row if x > 0]
  ```
- **Rule**: if a comprehension needs more than two `for`/`if` clauses, use a regular `for` loop with helper functions

### Item 29: Avoid Repeated Work in Comprehensions by Using Assignment Expressions
- The walrus operator (`:=`) avoids computing expensive expressions twice:
  ```python
  # Without walrus: compute_value() called twice
  results = [compute_value(x) for x in data if compute_value(x) > 0]

  # With walrus: computed once
  results = [y for x in data if (y := compute_value(x)) > 0]
  ```
- Especially valuable when the computation inside the comprehension is expensive

### Item 30: Consider Generators Instead of Returning Lists
- A function that builds and returns a `list` holds everything in memory:
  ```python
  def all_lines(path):
      result = []
      with open(path) as f:
          for line in f:
              result.append(line)
      return result
  ```
- A generator yields one item at a time — constant memory regardless of input size:
  ```python
  def all_lines(path):
      with open(path) as f:
          for line in f:
              yield line
  ```
- Use generators when the caller may not need all values, or when input is large/infinite

### Item 31: Be Defensive When Iterating Over Arguments
- A function that iterates over an argument multiple times will silently get no data on the second pass if given a generator/iterator (exhausted after first pass):
  ```python
  def normalize(numbers):
      total = sum(numbers)    # exhausts iterator
      for value in numbers:   # nothing left!
          yield value / total
  ```
- Solutions:
  1. Accept a callable that returns a new iterator: `numbers_fn = lambda: iter(data)`
  2. Accept a container (list/tuple) — always re-iterable
  3. Implement `__iter__` on a custom class that creates a fresh iterator each time
- Check for iterators passed where containers are expected:
  ```python
  if iter(numbers) is numbers:
      raise TypeError("Must supply a container, not an iterator")
  ```

### Item 32: Consider Generator Expressions for Large List Comprehensions
- A generator expression is a comprehension inside `()` — lazy, no list created:
  ```python
  it = (x**2 for x in range(1_000_000))  # no memory allocated yet
  ```
- Chain generator expressions to compose pipelines with zero intermediate lists:
  ```python
  roots = (x**0.5 for x in (x**2 for x in range(100)))
  ```

### Item 33: Compose Multiple Generators with `yield from`
- `yield from` delegates to a sub-generator — eliminates manual `for/yield` loops:
  ```python
  def chain(*iterables):
      for it in iterables:
          yield from it  # instead of: for item in it: yield item
  ```
- Cleaner, faster, and the inner generator runs at C speed
- Use whenever composing generator pipelines

### Item 34: Avoid Injecting Data into Generators with `send`
- `generator.send(value)` injects a value and receives the next `yield`
- This creates **bidirectional generators** — hard to understand and test
- Prefer a class with `__iter__` and state, or redesign using separate inputs/outputs
- `send` is occasionally useful for coroutine-like patterns but should be a last resort

### Item 35: Avoid Causing State Transitions in Generators with `throw`
- `generator.throw(exc)` injects an exception into a paused generator
- Like `send`, it makes control flow very hard to follow
- Use `try/finally` inside a generator for cleanup, but avoid `throw` from the outside
- If you need complex stateful control, use a class or `asyncio`

### Item 36: Consider `itertools` for Working with Iterators and Generators
Key tools organized by category:

**Linking iterators:**
| Function | Purpose |
|---|---|
| `chain(a, b)` | Concatenate iterables |
| `chain.from_iterable(it)` | Flatten one level |
| `cycle(it)` | Repeat iterable infinitely |
| `repeat(val, n)` | Repeat value n times |
| `zip_longest(*its)` | Zip, filling shorter with fillvalue |

**Filtering:**
| Function | Purpose |
|---|---|
| `islice(it, n)` | First n items |
| `takewhile(pred, it)` | Items while predicate holds |
| `dropwhile(pred, it)` | Items after predicate first fails |
| `filterfalse(pred, it)` | Opposite of `filter` |
| `compress(it, selectors)` | Items where selector is truthy |

**Producing combinations:**
| Function | Purpose |
|---|---|
| `accumulate(it, fn)` | Running accumulation |
| `product(*its)` | Cartesian product |
| `permutations(it, r)` | All ordered r-length permutations |
| `combinations(it, r)` | All unordered r-length combinations |

## Key Takeaways
- Use comprehensions for clarity, generators for memory efficiency
- Cap comprehension complexity at two nested `for`/`if` clauses
- Use `yield from` to compose generators cleanly
- Avoid `send` and `throw` — they make control flow opaque
- Know `itertools` — it eliminates many manual loop patterns

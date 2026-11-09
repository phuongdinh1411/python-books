# Chapter 1 – Pythonic Thinking

## Core Idea
**Pythonic code** follows the idioms, conventions, and style that the Python community has developed over decades. It isn't enforced by the compiler — it emerges from experience. Writing Pythonic code means writing code that is explicit, simple, and maximally readable.

## Items Summary

### Item 1: Know Which Version of Python You're Using
- Always use **Python 3** — Python 2 is end-of-life
- Check at runtime: `sys.version_info`
- Use `python3` explicitly to avoid ambiguity with system `python`

### Item 2: Follow the PEP 8 Style Guide
- **Naming**: `snake_case` for functions/variables; `CamelCase` for classes; `ALL_CAPS` for constants
- **Indentation**: 4 spaces (no tabs)
- **Line length**: 79 chars max
- **Imports**: one per line, stdlib → third-party → local order
- **Whitespace**: spaces around operators but not inside brackets
- Use `pycodestyle` / `flake8` / `ruff` to automate style checks
- Consistency matters more than personal preference

### Item 3: Know the Differences Between `bytes` and `str`
- `str` → Unicode text (sequence of code points)
- `bytes` → raw binary data (sequence of 8-bit values)
- They are **never interchangeable** — mixing them raises `TypeError`
- Always encode/decode at system boundaries (file I/O, network)
- Open text files with `encoding='utf-8'`; binary files with mode `'rb'`/`'wb'`

### Item 4: Prefer Interpolated F-Strings Over C-style Format Strings and `str.format`
- C-style `%` formatting: verbose, error-prone with type mismatches
- `str.format()`: cleaner but verbose for complex expressions
- **F-strings** (Python 3.6+): most readable, most concise, most powerful
  ```python
  name = "Alice"
  f"Hello, {name!r}, you are {len(name)} chars long"
  ```
- F-strings support arbitrary expressions, format specs, and `!r`/`!s`/`!a` conversions

### Item 5: Write Helper Functions Instead of Complex Expressions
- Complex one-liners are hard to read and debug
- If an expression needs a comment to understand — extract it into a named function
- Named functions communicate intent; complex expressions obscure it

### Item 6: Prefer Multiple Assignment Unpacking Over Indexing
- Unpacking is clearer and avoids magic index numbers:
  ```python
  # Bad
  item = ('Alice', 30)
  name = item[0]
  age = item[1]

  # Good
  name, age = item
  ```
- Works with any iterable; use `_` for values you don't need
- Nested unpacking is supported: `(a, (b, c)) = (1, (2, 3))`

### Item 7: Prefer `enumerate` Over `range`
- `range(len(items))` then indexing is error-prone and noisy
- `enumerate` gives both index and value cleanly:
  ```python
  for i, item in enumerate(items, start=1):
      print(f"{i}: {item}")
  ```

### Item 8: Use `zip` to Process Iterators in Parallel
- `zip` pairs items from multiple iterables:
  ```python
  for name, score in zip(names, scores):
      print(f"{name}: {score}")
  ```
- Stops at the shortest iterable — use `itertools.zip_longest` to include all
- Avoid manual index juggling with parallel lists

### Item 9: Avoid `else` Blocks After `for` and `while` Loops
- Python supports `for/else` and `while/else` — the `else` runs if the loop completed without `break`
- This is **counterintuitive** and surprises most readers
- Use a helper variable or helper function instead; avoid loop `else` for clarity

### Item 10: Prevent Repetition with Assignment Expressions (Walrus Operator `:=`)
- Python 3.8+: `:=` assigns and returns a value in one expression
- Reduces repetition in conditions:
  ```python
  # Without walrus
  count = fresh_fruit.get("lemon", 0)
  if count:
      make_lemonade(count)

  # With walrus
  if count := fresh_fruit.get("lemon", 0):
      make_lemonade(count)
  ```
- Useful in `while` loops to simulate `do-while`:
  ```python
  while chunk := file.read(8192):
      process(chunk)
  ```

## Key Takeaways
- Embrace Python's idioms — they exist because they make code clearer
- Use modern Python features (f-strings, walrus, unpacking) over older patterns
- Prefer readability over cleverness; the next person reading your code may be you

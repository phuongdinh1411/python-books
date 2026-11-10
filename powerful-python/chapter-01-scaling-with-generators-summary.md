# Chapter 1 – Scaling with Generators

## Core Idea
**Generator functions** are Python's most powerful tool for writing scalable, memory-efficient code. Instead of building entire lists upfront, generators produce values one at a time — lazily — so your code can handle arbitrarily large data sets without blowing up memory.

## Key Concepts

### Iterators and Iterables
- `iter(obj)` returns an **iterator** — an object that produces values one at a time via `next()`
- `next(iterator)` fetches the next value; raises `StopIteration` when exhausted
- An **iterable** is anything you can pass to `iter()` (lists, strings, files, etc.)
- A `for` loop is just syntactic sugar for calling `iter()` then `next()` in a loop

### Generator Functions
- A generator function uses `yield` instead of `return`
- Calling a generator function **returns a generator object** (an iterator), never a value directly
- Each `yield` is simultaneously an **exit point and a re-entry point** — the function pauses and resumes from there on the next `next()` call
```python
def gen_squares(max_root):
    for n in range(max_root):
        yield n ** 2
```
- Far more readable and maintainable than implementing `__iter__` / `__next__` manually
- Only as scalable as the **least scalable line** — avoid `readlines()` or large lists inside

### yield from
- Delegates to a sub-generator in one line, replacing a `for`/`yield` loop:
```python
def house_records_from_file(path):
    lines = lines_from_file(path)
    yield from house_records(lines)
```

### Generator Patterns
| Pattern | Description |
|---|---|
| **Source** | Takes non-iterator input, yields a stream (e.g., `lines_from_file`) |
| **Filter** | Passes a subset of input records through (e.g., `matching_lines`) |
| **Mapper** | Transforms each record 1-to-1 (e.g., `parse_log_records`) |
| **Fan Out** | One input record → multiple output records (e.g., `words_in_text`) |
| **Fan In** | Multiple input records → one output record (e.g., `house_records`) |
| **Sink** | Consumes a stream without producing another (e.g., `for record in ...: print(record)`) |

### Scalable Composability
- Design generators with consistent interfaces (accept iterators, yield iterators) so they can be **chained like pipeline stages**
- Ask: "What is the maximum memory footprint of this function?" — minimize it

### Built-in Iterators
- `range()` is a lazy, re-iterable **sequence**, not an iterator. `map()`, `filter()`, `zip()`, and `enumerate()` return iterators.

### The Iterator Protocol (formal)
An object is an **iterator** if it defines:
- `__next__()` — returns next item, raises `StopIteration` when done
- `__iter__()` — returns `self`

An object is **iterable** if it defines:
- `__iter__()` that creates and returns a fresh iterator, or
- `__getitem__()` with sequential integer indexing and `IndexError` at the end

## Key Takeaways
- Prefer generator functions over building lists when processing large or streamed data
- Chain generators into composable pipelines: source → filter → mapper → sink
- Use `yield from` to delegate to sub-generators cleanly
- Know the difference between **iterator** (single-pass producer) and **iterable** (anything accepted by `iter()`). Containers often provide fresh iterators; iterators themselves are also iterables.

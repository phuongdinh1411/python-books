# Chapter 17 – Iterators, Generators, and Classic Coroutines

## Core Idea
Python **groks** iterators: the iterator pattern is built deeply into the language. Generator functions are the idiomatic way to implement iterators. Classic coroutines (generators used with `.send()`) are the conceptual precursor to `async/await`.

## The Iterator Protocol
Python's `for` loop calls `iter(obj)` to get an iterator, then `next()` repeatedly:
```python
s = {1, 2, 3}
it = iter(s)
next(it)   # 1
next(it)   # 2
next(it)   # 3
next(it)   # StopIteration
```
An **iterable** has `__iter__`; an **iterator** has both `__iter__` (returns self) and `__next__`.

**Rule**: never make the iterable and the iterator the same object — the iterator should be a separate, disposable object returned by `__iter__`.

## Classic Iterator (verbose)
```python
class SentenceIterator:
    def __init__(self, words):
        self._words = words
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._words):
            raise StopIteration
        word = self._words[self._index]
        self._index += 1
        return word
```

## Generator Functions (Pythonic)
A function with `yield` returns a **generator object**:
```python
def sentence(text):
    for word in re.findall(r'\w+', text):
        yield word   # pauses here, sends value to caller
```
Each call to `next()` resumes from where it left off. No iterator class needed.

## Lazy Generators
```python
def sentence(text):
    pattern = re.compile(r'\w+')
    for match in pattern.finditer(text):
        yield match.group()   # produce one word at a time, no full list in memory
```

## Generator Expressions
```python
(x**2 for x in range(10))   # generator expression
list(x**2 for x in range(10))  # or pass directly to list/sum/etc.
```
Prefer generator expressions for simple cases; generator functions for anything complex.

## Standard Library Generator Functions
| Function | Effect |
|---|---|
| `itertools.count(start, step)` | Infinite counter |
| `itertools.cycle(it)` | Infinite cycle over iterable |
| `itertools.islice(it, stop)` | Lazy slice |
| `itertools.chain(*its)` | Concatenate iterables |
| `itertools.zip_longest(*its)` | Zip filling shorter with `fillvalue` |
| `itertools.product(*its)` | Cartesian product |
| `itertools.groupby(it, key)` | Group consecutive items by key |
| `itertools.takewhile(pred, it)` | Yield while predicate true |
| `itertools.dropwhile(pred, it)` | Skip while predicate true |
| `enumerate(it, start=0)` | `(index, item)` pairs |
| `map(f, it)` | Apply `f` to each item |
| `filter(pred, it)` | Keep items where `pred` is truthy |
| `zip(*its)` | Pair items from multiple iterables |

## Reducing Functions
Turn an iterable into a single value:
```python
sum, min, max, any, all   # built-ins
functools.reduce(f, it)   # general fold
```

## `yield from`
Delegates to a sub-generator, forwarding `next()`, `.send()`, and `.throw()`:
```python
def chain(*iterables):
    for it in iterables:
        yield from it

list(chain([1, 2], [3, 4]))  # [1, 2, 3, 4]
```
Also used to traverse nested structures:
```python
def flatten(tree):
    for item in tree:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item
```

## Classic Coroutines
Generators used as coroutines via `.send(value)`:
```python
def averager():
    total = 0.0
    count = 0
    average = None
    while True:
        value = yield average   # pauses; receives sent value
        total += value
        count += 1
        average = total / count

avg = averager()
next(avg)       # prime: advance to first yield
avg.send(10)    # 10.0
avg.send(30)    # 20.0
```
- Must be **primed** with `next()` or `.send(None)` before the first `.send(value)`
- `.throw(exc)` injects an exception at the `yield` point
- `.close()` raises `GeneratorExit` at the `yield`
- `StopIteration.value` holds the `return` value of the coroutine

Classic coroutines are the conceptual foundation of `async/await` — native coroutines (Chapter 21) replace them for async I/O.

## Closing Thoughts
Python's iterator machinery is invisible in use but powerful when extended. Generator functions are almost always the right tool for custom iteration — they are simpler than iterator classes and lazy by design. `yield from` composes generators and is the backbone of coroutine delegation. Classic coroutines are largely superseded by `async def` but understanding them illuminates how `await` works internally.

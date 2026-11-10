# Powerful Python — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how do you move from small scripts to expressive, reusable Python programs?

**Answer:** learn the protocols and composition tools already built into Python. Generators stream data, functions carry behavior, decorators add reusable wrappers, classes protect state, and modules provide stable boundaries.

**Mental model:** source → filter → transform → sink, with clear APIs and tests around each stage. Prefer the simplest abstraction that expresses the job.

**You should already know:** loops, functions, collections, and basic classes. This is a next-step book, not a first introduction to Python syntax.

## Quick Route (About 25–40 Minutes)

1. [Ch. 1: Generators](chapter-01-scaling-with-generators-summary.md) — distinguish iterables from single-pass iterators.
2. [Ch. 2: Comprehensions](chapter-02-comprehensions-summary.md) — decide whether to materialize or stream.
3. [Ch. 3: Functions](chapter-03-advanced-functions-summary.md) — pass behavior with callables and `key=`.
4. [Ch. 5: Exceptions](chapter-05-exceptions-and-errors-summary.md) — handle expected failures without hiding bugs.
5. [Ch. 7: Testing](chapter-07-automated-testing-summary.md) — turn expected behavior into repeatable checks.

Then add decorators and classes when a project gives you a reason. Do not start by memorizing metaprogramming patterns.

## Chapter Map

| Chapter | What to retain |
|---|---|
| [1 — Scaling with generators](chapter-01-scaling-with-generators-summary.md) | Lazy production; each stage must avoid unbounded storage |
| [2 — Comprehensions](chapter-02-comprehensions-summary.md) | Clear transformations; lists for reuse, generators for streaming |
| [3 — Advanced functions](chapter-03-advanced-functions-summary.md) | Packing/unpacking arguments and passing callable behavior |
| [4 — Decorators](chapter-04-decorators-summary.md) | A decorator transforms a callable; scope controls state lifetime |
| [5 — Exceptions and errors](chapter-05-exceptions-and-errors-summary.md) | Narrow catches, meaningful errors, explicit cleanup |
| [6 — Classes and objects](chapter-06-classes-and-objects-summary.md) | Properties, alternate constructors, callbacks, useful protocols |
| [7 — Automated testing](chapter-07-automated-testing-summary.md) | Independent tests and the red → green → refactor loop |
| [8 — Module organization](chapter-08-module-organization-summary.md) | Stable imports, main guards, minimal import-time side effects |
| [9 — Logging](chapter-09-logging-summary.md) | Severity, deferred formatting, handlers, and formatters |

## Do Not Confuse

- **Iterable vs. iterator:** every iterator is iterable; not every iterable is an iterator. `range` can be traversed repeatedly, a generator normally cannot.
- **Lazy vs. constant memory:** a generator can still store a huge collection internally. Inspect retained state and downstream consumers.
- **Decorator vs. ordinary call:** decoration happens at definition time; wrapper code runs at call time. Preserve metadata with `functools.wraps`.
- **Properties vs. security:** a property can validate normal writes; underscore naming is a convention, not access control.

## Practice (10–20 Minutes)

Count valid nonnegative integers from a stream without building an intermediate list:

```python
def valid_numbers(lines):
    for line in lines:
        try:
            number = int(line.strip())
        except ValueError:
            continue
        if number >= 0:
            yield number

lines = iter(["10", "bad", "-2", "5"])
assert sum(valid_numbers(lines)) == 15
assert list(lines) == []  # the input iterator was consumed
```

Extend it to read a file inside `with open(..., encoding="utf-8")`. Add tests for empty input, whitespace, malformed text, and all-negative values. Keep the sum operation inside the file context so resource lifetime is explicit.

## Self-Check

1. Why would replacing the input with a list allow another pass, but not make the same generator reusable?
2. Where should decorator state live if it must be separate for each decorated function?
3. Why is `except Exception: pass` a poor response to an unexpected failure?
4. When would you choose a class over a stateless function?

**Answer cues:** fresh iterator vs. exhausted producer; enclosing decorator scope; hides bugs; persistent state/invariants or a meaningful multi-operation interface.

**Next:** [Effective Python](../effective-python/README.md) for API trade-offs and common traps.

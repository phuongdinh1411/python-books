# Effective Python — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** which everyday Python choices make code clearer and prevent subtle bugs?

**Answer:** use idiomatic collection operations, explicit function contracts, simple object interfaces, appropriate concurrency, and disciplined testing. This is a catalog of decisions, not a tutorial you must read linearly.

**Mental model:** for each item, learn the trap → preferred pattern → reason → exception. Treat recommendations as defaults with context, not language laws.

**Coverage note:** these summaries follow the 90-item structure associated with the second edition. Do not assume item numbers match later editions.

## Quick Route (About 30–45 Minutes)

1. [Ch. 1: Pythonic thinking](chapter-01-pythonic-thinking-summary.md) — unpacking, `enumerate`, `zip`, and readability.
2. [Ch. 2: Collections](chapter-02-lists-and-dictionaries-summary.md) — sorting, missing keys, and ordering contracts.
3. [Ch. 3: Functions](chapter-03-functions-summary.md) — dynamic defaults, exceptions, and keyword-only options.
4. [Ch. 4: Generators](chapter-04-comprehensions-and-generators-summary.md) — laziness and exhausted inputs.
5. [Ch. 9: Testing/debugging](chapter-09-testing-and-debugging-summary.md) — make behavior observable and testable.

Read Ch. 7 for concurrency work and Ch. 8 for production robustness. Save Ch. 6's dynamic class machinery until you need it.

## Chapter Map

| Chapter / Items | What to retain |
|---|---|
| [1 / 1–10 — Pythonic thinking](chapter-01-pythonic-thinking-summary.md) | Prefer clear idioms to manual indexing and clever expressions |
| [2 / 11–18 — Lists and dictionaries](chapter-02-lists-and-dictionaries-summary.md) | Use collection semantics deliberately: slice, sort, default, order |
| [3 / 19–26 — Functions](chapter-03-functions-summary.md) | Named contracts, safe defaults, explicit argument modes, wrapper metadata |
| [4 / 27–36 — Comprehensions and generators](chapter-04-comprehensions-and-generators-summary.md) | Bound expression complexity and handle single-pass inputs |
| [5 / 37–43 — Classes and interfaces](chapter-05-classes-and-interfaces-summary.md) | Compose state and behavior; cooperate with Python protocols |
| [6 / 44–51 — Metaclasses and attributes](chapter-06-metaclasses-and-attributes-summary.md) | Attributes → properties → descriptors/hooks only as needed |
| [7 / 52–64 — Concurrency and parallelism](chapter-07-concurrency-and-parallelism-summary.md) | Choose by I/O vs. CPU bottleneck and required concurrency |
| [8 / 65–74 — Robustness and performance](chapter-08-robustness-and-performance-summary.md) | Cleanup, precision, profiling, and workload-specific structures |
| [9 / 75–81 — Testing and debugging](chapter-09-testing-and-debugging-summary.md) | Isolation, targeted mocks, debugging, and allocation tracing |
| [10 / 82–90 — Collaboration](chapter-10-collaboration-summary.md) | Stable package APIs, documented contracts, controlled dependencies |

## Do Not Confuse

- **A guideline vs. a guarantee:** “prefer,” “consider,” and “avoid” describe trade-offs. `map` with a named function or a loop `else` can still be appropriate.
- **`dict` vs. any mapping:** insertion order is guaranteed for `dict` from 3.7, not for every custom mapping.
- **`get` vs. default creation:** `d.get(key, [])` does not store that list. Use `defaultdict` when missing-key access should create state.
- **Thread offloading vs. CPU parallelism:** an executor with `None` uses threads. CPU-bound Python usually needs an explicit process executor on GIL-enabled CPython.

## Practice (10–20 Minutes)

Build an API with an explicit keyword-only choice and a safe dynamic default:

```python
def record_visit(name, city, *, visits=None):
    if visits is None:
        visits = {}
    visits.setdefault(name, []).append(city)
    return visits

first = record_visit("Alice", "Paris")
second = record_visit("Bob", "Rome")
assert first == {"Alice": ["Paris"]}
assert second == {"Bob": ["Rome"]}  # no shared default state
record_visit("Alice", "Berlin", visits=first)
assert first["Alice"] == ["Paris", "Berlin"]
```

Replace the default with `{}` and explain why the isolation assertion fails. Then build a stateful version backed by `defaultdict(list)` and document whether callers may mutate the returned collection.

## Self-Check

1. When is a default argument evaluated?
2. Why can a two-pass algorithm silently fail on a generator?
3. Does `bisect.insort` make list insertion O(log n)?
4. Why can a `finally` block introduce a new bug if acquisition failed?

**Answer cues:** function definition; first pass exhausts input; search is O(log n), shifting is O(n); resource may not exist and cleanup can mask the original error.

**Next:** [Robust Python](../robust-python/README.md) for larger-scale contracts, or [High Performance Python](../high-performance-python/README.md) when measurement shows a bottleneck.

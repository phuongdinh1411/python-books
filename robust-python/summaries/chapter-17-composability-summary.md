# Chapter 17 – Composability

## Core Idea
**Composability** means building small, self-contained, reusable components with minimal interdependencies. Composable code can be mixed and matched to build new solutions — making systems future-proof without prediction.

## What Is Composability?
> Build small, discrete, reusable pieces. Future developers pick what they need and combine them.

Like a spice rack: individual spices are simple, but their combinations create infinite variety. A non-composable "all-in-one spice blend" is convenient for one dish but useless for everything else.

### Benefits
- **Small components** → easier to read and understand in isolation
- **Fewer dependencies** → fewer ripple effects when things change
- **No embedded business logic** → components can solve problems you never anticipated

## Policy vs. Mechanism

A foundational composability principle from Eric Raymond:
- **Mechanism**: *how* something is done (the reusable primitive)
- **Policy**: *what* is done with it (the specific business rule)

Keep mechanisms separate from policies:
```python
# Mechanism: how to retry (reusable)
def retry(fn, max_attempts: int, delay: float):
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception:
            time.sleep(delay)
    raise MaxRetriesExceeded()

# Policy: what to retry (specific)
retry(fetch_menu_data, max_attempts=3, delay=1.0)
```
The `retry` mechanism knows nothing about menus; it works for anything. This makes it composable.

## Composing on a Smaller Scale

### Composing Functions
Use higher-order functions and function composition:
```python
from functools import reduce

def compose(*fns):
    return reduce(lambda f, g: lambda x: f(g(x)), fns)

normalize = compose(strip_whitespace, lowercase, remove_punctuation)
```
- Each function does one thing
- Combinations create complex behaviors without monolithic functions
- Easier to test each step in isolation

**Partial application** with `functools.partial`:
```python
from functools import partial

add_tax = partial(apply_rate, rate=0.08)
# add_tax is now reusable as a single-argument function
```

### Composing Algorithms
Use the **Strategy pattern** and **iterator chaining** (`itertools`) to compose processing pipelines:
```python
import itertools

pipeline = itertools.chain(
    filter(is_vegetarian, dishes),
    map(apply_discount, featured_dishes)
)
```
- Small, single-purpose functions chained together
- Each step is independently testable and reusable
- Adding a new step doesn't require modifying existing ones

## Non-Composable Design: Signs to Watch For
- God functions: one function that does 10 things
- Deep nesting: logic buried 5 levels in
- Global state: functions that depend on shared mutable state
- Hard-coded dependencies: functions that create their own dependencies instead of accepting them

## Closing Thoughts
Composability is the design quality that makes a codebase survive contact with an unpredictable future. Build small mechanisms, keep policy separate, and favor function/algorithm composition over monolithic implementations. The result is a system where new features are assembled from existing pieces rather than written from scratch.

# Chapter 23 – Property-Based Testing

## Core Idea
Traditional tests check specific examples. **Property-based testing** checks that invariants hold for *any* input a generator can produce — discovering edge cases you'd never think to write manually.

## The Limitation of Example-Based Tests
```python
def test_meal_recommendation():
    meal = recommend_meal(target_calories=900)
    assert meal.total_calories < 900
```
This tests one scenario. What about `target_calories=1`, `999999`, `-1`, `0`? Each could behave differently. Writing all those cases manually is impractical. Property-based testing automates this.

## Property-Based Testing with Hypothesis
Hypothesis generates test inputs automatically and searches for inputs that violate your properties (invariants):

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=5000))
def test_meal_recommendation_under_target(target_calories: int):
    meal = recommend_meal(target_calories=target_calories)
    assert meal.total_calories < target_calories
```
- Hypothesis generates hundreds of random integers within the range
- If it finds a failing input, it **shrinks** toward a simpler failing case (not a proof of the globally smallest input)
- Saved failures can be replayed through the example database; keep critical regressions as explicit examples/tests too

## The Magic of Hypothesis

### Shrinking
When Hypothesis finds a failing input, it automatically simplifies it:
```
Failing input found: target_calories=3847
Shrinking...
Minimal failing input: target_calories=3
```
This gives you the smallest, clearest reproduction case automatically.

### Falsifying Example Database
Hypothesis stores previously failing examples in `.hypothesis/` and always reruns them — ensuring regressions are caught even if the random seed changes.

### Contrast with Traditional Tests
| | Example-Based | Property-Based |
|---|---|---|
| Inputs | Hand-chosen | Auto-generated |
| Edge cases | Easy to miss | Systematically explored |
| Failure messages | At the chosen input | At the smallest failing input |
| Coverage | Limited | Broad |
| Writing effort | High for thorough coverage | Low |

## Getting the Most Out of Hypothesis

### Hypothesis Strategies
Strategies are generators for test data:

| Strategy | Generates |
|---|---|
| `st.integers(min_value=0)` | Non-negative integers |
| `st.text()` | Unicode strings |
| `st.floats(allow_nan=False, allow_infinity=False)` | Finite floats |
| `st.lists(st.integers(), min_size=1)` | Non-empty integer lists |
| `st.one_of(st.integers(), st.text())` | Either an int or a string |
| `st.builds(MyClass, field=st.integers())` | Instances of MyClass |
| `st.from_type(MyDataclass)` | Inferred from type hints |

Compose strategies for complex inputs:
```python
@given(st.lists(st.integers(min_value=0, max_value=1_000_000), min_size=1, max_size=100))
def test_average_is_within_bounds(values: list[int]):
    result = average(values)
    assert min(values) <= result <= max(values)
```

This bounded-integer strategy keeps a simple float-based average away from infinity and overflow. If arbitrary floats are part of the API, test NaN, infinity, overflow, and rounding behavior separately with an explicit numerical contract.

### Generating Algorithms (Stateful Testing)
Hypothesis `RuleBasedStateMachine` tests stateful systems:
```python
from collections import deque
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, precondition

class QueueMachine(RuleBasedStateMachine):
    @initialize()
    def init(self):
        self.queue = deque()
        self.model = []

    @rule(value=st.integers())
    def enqueue(self, value):
        self.queue.append(value)
        self.model.append(value)

    @precondition(lambda self: bool(self.model))
    @rule()
    def dequeue(self):
        assert self.queue.popleft() == self.model.pop(0)

TestQueue = QueueMachine.TestCase  # enables unittest/pytest discovery
```
Hypothesis generates sequences of operations and finds sequences that break invariants.

## What Makes a Good Property?
- **Invariants**: a value is always within bounds
- **Round-trip properties**: `decode(encode(x)) == x`
- **Idempotent properties**: `f(f(x)) == f(x)` (e.g., sorting)
- **Commutativity**: `f(a, b) == f(b, a)` (e.g., addition)
- **Metamorphic properties**: `result_with_discount <= result_without_discount`

## Closing Thoughts
Hypothesis is one of the most powerful testing tools in Python. It doesn't replace example-based tests — it complements them by exploring the space your examples don't cover. Every time it finds a surprising edge case, you've discovered a real bug you'd have missed otherwise.

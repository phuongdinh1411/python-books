# Robust Python — Learner Guide

[All books](../README.md)

## The Book in One Minute

**Main question:** how can code communicate its intent so future changes are safer?

**Answer:** choose meaningful types, enforce constraints at boundaries, design substitutable interfaces, manage dependencies, and test behavior with several complementary techniques.

**Mental model:** untrusted input → validated domain values → small operations behind explicit interfaces → observable, tested outcomes.

The central theme is maintainability, not “add annotations everywhere.” Static checking, runtime validation, encapsulation, and tests provide different protections.

## Quick Route (About 30–45 Minutes)

1. [Ch. 1: Intent](chapter-01-introduction-to-robust-python-summary.md) — understand the book's purpose.
2. [Ch. 4: Constraints](chapter-04-constraining-types-summary.md) — model valid alternatives and missing values.
3. [Ch. 9: Data classes](chapter-09-user-defined-types-data-classes-summary.md) — name domain data.
4. [Ch. 13: Protocols](chapter-13-protocols-summary.md) — depend on required behavior rather than concrete implementations.
5. [Ch. 14: Runtime validation](chapter-14-runtime-checking-with-pydantic-summary.md) — check external input.
6. [Ch. 21: Test strategy](chapter-21-testing-strategy-summary.md) and [Ch. 23: Properties](chapter-23-property-based-testing-summary.md) — check outcomes and invariants.

If typing is new, read Ch. 2–3 first. If a codebase is already typed, prioritize Ch. 11–19 on interfaces and change.

## Chapter Map

### Types and Adoption

| Chapter | What to retain |
|---|---|
| [1 — Introduction](chapter-01-introduction-to-robust-python-summary.md) | Robustness starts with communicating intent |
| [2 — Python types](chapter-02-introduction-to-python-types-summary.md) | Runtime behavior and semantic meaning are different roles |
| [3 — Annotations](chapter-03-type-annotations-summary.md) | Hints enable static checks; Python does not enforce them automatically |
| [4 — Constraining types](chapter-04-constraining-types-summary.md) | Model alternatives, missing values, distinct IDs, and constants |
| [5 — Collection types](chapter-05-collection-types-summary.md) | Describe both stored data and required operations |
| [6 — Typechecker configuration](chapter-06-customizing-your-typechecker-summary.md) | Choose useful checks and progressively increase strictness |
| [7 — Practical adoption](chapter-07-adopting-typechecking-practically-summary.md) | Target high-risk/high-churn code, not an all-at-once rewrite |

### Domain Values and Interfaces

| Chapter | What to retain |
|---|---|
| [8 — Enums](chapter-08-user-defined-types-enums-summary.md) | Name a closed set of domain choices |
| [9 — Data classes](chapter-09-user-defined-types-data-classes-summary.md) | Group named fields; distinguish frozen from deeply immutable |
| [10 — Classes](chapter-10-user-defined-types-classes-summary.md) | Establish and preserve invariants through all mutation paths |
| [11 — Interfaces](chapter-11-defining-your-interfaces-summary.md) | Design from call sites and use natural Python protocols |
| [12 — Subtyping](chapter-12-subtyping-summary.md) | Preserve the parent contract, not merely structural similarity |
| [13 — Protocols](chapter-13-protocols-summary.md) | Structural interfaces support unrelated implementations |
| [14 — Pydantic](chapter-14-runtime-checking-with-pydantic-summary.md) | Parse/validate at boundaries; distinguish coercion from strict checks |

### Designing for Change

| Chapter | What to retain |
|---|---|
| [15 — Extensibility](chapter-15-extensibility-summary.md) | Add extension points only where variation justifies them |
| [16 — Dependencies](chapter-16-dependencies-summary.md) | Recognize import, behavioral, and ordering dependencies |
| [17 — Composability](chapter-17-composability-summary.md) | Separate reusable mechanism from application policy |
| [18 — Events](chapter-18-event-driven-architecture-summary.md) | Decouple reactions, but design delivery, ordering, and failures |
| [19 — Plugins](chapter-19-pluggable-python-summary.md) | Keep extension contracts small, stable, and validated |

### Verifying Behavior

| Chapter | What to retain |
|---|---|
| [20 — Static analysis](chapter-20-static-analysis-summary.md) | Automate useful type, lint, complexity, and security checks |
| [21 — Test strategy](chapter-21-testing-strategy-summary.md) | Spend test effort according to risk; prefer behavioral assertions |
| [22 — Acceptance testing](chapter-22-acceptance-testing-summary.md) | Agree with stakeholders on examples of success |
| [23 — Property-based testing](chapter-23-property-based-testing-summary.md) | Search generated inputs for violations; shrinking aids diagnosis |
| [24 — Mutation testing](chapter-24-mutation-testing-summary.md) | Ask whether tests detect changes, not just execute lines |

## Do Not Confuse

- **Annotated vs. validated:** `TypedDict`, `NewType`, and `Literal` do not automatically check external data at runtime.
- **Optional vs. optional argument:** `T | None` means the value may be `None`; a default determines whether a caller may omit the argument.
- **Frozen vs. deeply immutable:** frozen dataclass fields cannot normally be reassigned, but a list field can still mutate.
- **Protocol presence vs. signature validation:** `runtime_checkable` is a shallow runtime check; a static checker verifies compatible method signatures.
- **Coverage vs. correctness:** executing a line does not show that an assertion checks its effect. Mutation testing adds evidence, not proof.

## Practice (15–25 Minutes)

Model an order and inject a notification dependency:

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Order:
    quantity: int

    def __post_init__(self):
        if self.quantity < 1:
            raise ValueError("quantity must be positive")

class Notifier(Protocol):
    def send(self, message: str) -> None: ...

def confirm(order: Order, notifier: Notifier) -> None:
    notifier.send(f"Confirmed {order.quantity} items")

class RecordingNotifier:
    def __init__(self):
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)

notifier = RecordingNotifier()
confirm(Order(2), notifier)
assert notifier.messages == ["Confirmed 2 items"]
```

Add tests rejecting zero and negative quantities. Explain why `quantity: int` alone would not reject zero. If input comes from JSON, add a validated boundary model rather than relying on the dataclass annotation to check runtime types.

## Self-Check

1. What belongs in runtime validation rather than static typing?
2. How would a subclass strengthen a precondition and violate substitutability?
3. Which dependency makes `connect → query → close` necessary, and how can you encode it?
4. Why might a surviving mutant not justify a new test?

**Answer cues:** external types/value ranges; accept fewer valid parent inputs; temporal dependency, scoped context/state model; equivalent behavior for valid inputs.

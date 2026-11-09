# Chapter 15 – Extensibility

## Core Idea
**Extensibility** is the ability to add new functionality *without modifying existing code*. It is the foundation of Part III because it determines how easily a codebase can evolve without accumulating bugs and technical debt.

## What Is Extensibility?
- Software will change — business requirements evolve, features are added, architectures shift
- Non-extensible code requires modifying existing, tested logic every time something new is added
- Each modification is a risk: you may introduce bugs in code that already works
- Extensible code provides **extension points** — places where new behavior plugs in without touching the core

### The Restaurant Notification Example
A notification system starts by supporting one supplier. Soon it needs SMS, email, and Slack notifications. Without extensibility:
```python
def notify(method: str, message: str):
    if method == "email":
        send_email(message)
    elif method == "sms":
        send_sms(message)
    elif method == "slack":
        send_slack(message)
    # Add more if/elif every time a new method is needed...
```
Every new channel requires modifying this function — risky and tedious.

### The Redesign
With extensibility:
```python
class Notifier(Protocol):
    def send(self, message: str) -> None: ...

def notify(notifier: Notifier, message: str) -> None:
    notifier.send(message)
```
New notification channels are added by creating new classes — no existing code changes.

## Open-Closed Principle (OCP)
> "Software entities should be **open for extension** but **closed for modification**."
> — Bertrand Meyer

- **Open for extension**: add new behavior
- **Closed for modification**: don't change what already exists and works

OCP is the design principle that makes extensibility achievable.

### Detecting OCP Violations
Signs that code violates OCP:
- Long `if/elif/else` or `match` chains that grow with new types
- `isinstance()` checks scattered through the codebase
- Every time you add a new variant, you touch multiple files
- "Shotgun surgery": one logical change requires edits in many places

### Applying OCP
Replace type-switch logic with polymorphism or protocols:
- Define an interface (ABC or Protocol)
- Each variant implements the interface
- Core logic depends only on the interface — new variants add files, not edits

### Drawbacks
- OCP adds abstraction; adds indirection
- Can be overkill for code that changes rarely or has very few variants
- Apply OCP to code that **changes frequently**, not everywhere blindly

## Closing Thoughts
Extensibility is not free — it requires up-front design thought. But in areas of your codebase that evolve frequently, the investment pays off every time a new feature is added without risk of regression. The Open-Closed Principle is the practical guide to achieving it.

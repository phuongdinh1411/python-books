# Chapter 3 – Type Annotations

## Core Idea
Type annotations are Python's mechanism for adding **explicit type information** to code. They don't affect runtime behavior but dramatically improve readability, tooling, and robustness.

## What Are Type Annotations?
Syntax introduced in Python 3.5 to hint expected types on variables, function parameters, and return values:

```python
def close_kitchen_if_past_close(point_in_time: datetime.datetime) -> None:
    ...

price: float = 9.99
```

- Annotations are **hints**, not enforcement — Python does not check them at runtime
- They exist primarily for *tools* (typecheckers, IDEs) and *humans* (developers reading the code)

## Benefits

### Autocomplete
- IDEs use annotations to provide accurate method/property suggestions
- Reduces typos and exploration time when working with unfamiliar code

### Typecheckers
- Tools like **mypy**, **Pyright**, and **Pyre** read annotations and flag inconsistencies statically (before running code)
- Catch entire classes of bugs at development time, not in production
- Example: passing a `str` where a `datetime` is expected is caught immediately

### Spotting Bugs Early
- Annotated code makes incorrect assumptions *visible*
- A typechecker can flag "you're returning `None` but the caller expects `str`" — without writing a test

## When to Use Type Annotations
- **New code**: annotate from the start — it's cheapest when greenfield
- **Public APIs / interfaces**: always annotate — they are the contract with callers
- **Complex functions**: annotate when logic is non-trivial or types are not obvious
- **Legacy code**: add annotations incrementally, targeting high-risk areas first (see Chapter 7)
- Not every single variable needs an annotation — annotate function boundaries and key variables

## What Annotations Don't Do
- They do **not** enforce anything at runtime (a `str` can still be passed where `int` is expected)
- They are not a replacement for tests — they catch different classes of errors
- They require a typechecker to be useful beyond documentation

## Closing Thoughts
Type annotations are one of the highest-ROI investments in a Python codebase. They act as verified documentation — the intent is written down and a tool can check that the code matches it. They are the foundation for everything in Part I of the book.

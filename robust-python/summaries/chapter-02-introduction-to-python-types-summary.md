# Chapter 2 – Introduction to Python Types

## Core Idea
A **type is a communication method** — it conveys information both to the Python runtime and to other developers. Understanding this dual role is essential for writing maintainable code.

## What's in a Type?

### Mechanical Representation
- At the CPU level, everything is bits. Without type information, `01010000 01000001 01010100` could be the integer `5259604` or the string `"PAT"`.
- Python uses type information to interpret memory correctly at runtime.
- Types tell Python **how to behave**: what operations are valid, how much memory to allocate, how to compare values.

### Semantic Representation
- Beyond the machine, types carry **meaning** to human readers.
- Example: a function taking `datetime.datetime` vs. one taking a raw `float` for "time" — the former expresses far more about intent.
- Types are documentation that the type system can actually check.

## Typing Systems

### Strong vs. Weak Typing
- **Strong**: type errors are not silently ignored (Python is strong — `"5" + 5` raises `TypeError`)
- **Weak**: implicit coercions allow mixing types freely (e.g., JavaScript `"5" + 5 == "55"`)
- Stronger typing catches more errors early

### Dynamic vs. Static Typing
- **Dynamic** (Python): types are attached to *values* at runtime; variables can be rebound to any type
- **Static** (Java, C++): types are attached to *variables* and checked at compile time
- Dynamic typing offers flexibility but shifts error detection to runtime

### Duck Typing
- Python's practical superpower: if an object supports the required behaviors, it can be used — regardless of its declared type
- "If it walks like a duck and quacks like a duck, it's a duck"
- Enables flexible, reusable code but can obscure intent — a key tension the book addresses

## Why This Matters for Robustness
- Understanding Python's type system helps you make deliberate choices about how to express intent
- Dynamic typing is a feature *and* a liability — you gain flexibility but lose compile-time guarantees
- Type annotations (covered in Chapter 3) bridge the gap: keep Python's dynamism while adding static safety

## Closing Thoughts
Types are more than a runtime necessity — they are a vocabulary for communicating with future developers. Choosing types thoughtfully is the foundation of robust Python.

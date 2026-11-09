# Chapter 16 – Dependencies

## Core Idea
Every codebase is a graph of dependencies. Unmanaged, they become **spaghetti** — tangled, fragile, and impossible to change safely. Understanding and controlling your dependency graph is essential for maintaining a robust, extensible codebase.

## Relationships
A dependency exists when one piece of code requires another to behave in a specific way. Dependencies provide code reuse but introduce coupling — a change in the depended-upon code can break everything that depends on it.

## Three Types of Dependencies

### 1. Physical Dependencies
The most visible: module A imports module B.
```python
# module_a.py
from module_b import SomeClass
```
- Creates a hard link: `module_a` cannot run without `module_b`
- Risks: circular imports, slow import chains, tight coupling
- Manage by: keeping dependencies directional (no cycles), using dependency injection

**Dependency inversion**: depend on abstractions, not concretions:
```python
# Bad: depends on a specific class
class OrderProcessor:
    def __init__(self):
        self._notifier = EmailNotifier()  # hard dependency

# Good: depends on an abstraction
class OrderProcessor:
    def __init__(self, notifier: Notifier):
        self._notifier = notifier  # injected dependency
```

### 2. Logical Dependencies
Subtler: module A doesn't import module B, but A relies on B's behavior:
- A assumes B will always return a sorted list
- A assumes B's global state is in a certain condition
- Not visible in imports; only discovered when things break

Manage by: making assumptions explicit via types, assertions, and documentation; minimizing shared mutable state.

### 3. Temporal Dependencies
The trickiest: code must execute in a specific order:
```python
db.connect()    # must come before
db.query(...)   # must come before
db.close()      # must come last
```
If the order is violated, bugs or errors occur — but nothing in the type system prevents it.

Manage by: using context managers, builder patterns, or state machines to enforce ordering structurally.

## Visualizing Your Dependencies

### Visualizing Packages
Use `pipdeptree` to see your third-party dependency tree:
```bash
pipdeptree
```
Spot transitive dependencies and version conflicts.

### Visualizing Imports
Use `pydeps` or `import-linter` to graph module-level imports:
```bash
pydeps my_package
```
Visualize as a directed graph; look for cycles and unexpected edges.

### Visualizing Function Calls
Use `pycallgraph2` to generate a runtime call graph:
- Shows which functions call which
- Helps identify hot spots and unexpected coupling

### Interpreting Your Dependency Graph
Healthy signs:
- **Directed acyclic graph (DAG)**: no cycles
- **Layered architecture**: high-level modules depend on low-level, never the reverse
- **Few long-range edges**: isolated modules with well-defined interfaces

Danger signs:
- **Cycles**: mutual imports indicate tight coupling
- **Hub nodes**: one module imported by everything — a change there ripples everywhere
- **Violation of layer boundaries**: business logic importing infrastructure details

## Closing Thoughts
Dependencies are the architecture of your system. Visualize them regularly, apply dependency inversion to break tight couplings, and distinguish physical, logical, and temporal dependencies to address each appropriately. A clean dependency graph is a maintainable codebase.

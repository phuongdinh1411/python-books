# Chapter 7 – Adopting Typechecking Practically

## Core Idea
Most codebases are not greenfield. Adding type annotations to a **legacy/brown-field codebase** requires strategy — you can't annotate everything at once, and the payoff must exceed the cost. This chapter provides a practical roadmap.

## The Trade-offs
- **Cost**: time to write annotations, address new typechecker errors, keep them up to date
- **Benefit**: caught bugs, improved readability, better IDE support, safer refactoring
- The break-even point comes sooner than expected — especially in high-churn areas

> Michael Feathers: "Legacy code is code without tests." Viafore's extension: it's code where you can no longer ask the original author what it means. Annotations replace that conversation.

## Strategy: Breaking Even Earlier

### 1. Find Your Pain Points
- Where do bugs most often originate?
- Which modules are changed most frequently?
- Where does onboarding take the longest?
- Start annotating there — the ROI is highest in high-churn, high-complexity code

### 2. Target Code Strategically
Three approaches:

| Approach | Description | Best For |
|---|---|---|
| **Target a module** | Annotate one module completely | Isolated modules with clear interfaces |
| **Target a function path** | Annotate all functions in a call chain | Critical paths prone to bugs |
| **Strangler Fig** | Annotate new code only; let old code age out | Large codebases where full coverage is impractical |

Avoid trying to annotate the whole codebase at once — it's demoralizing and low-ROI.

### 3. Lean on Your Tooling
**MonkeyType** — automatically infers and inserts annotations by running your test suite:
```bash
monkeytype run pytest
monkeytype apply my_module
```
- Great for generating a first pass; requires human review and cleanup
- Generates runtime-observed types, which may be too specific (e.g., `int` instead of `float`)

**Pytype** (Google) — infers types statically without running code:
- More conservative than MonkeyType but safer for untested code
- Can generate stub files (`.pyi`)

**pyright's `--createstubs`** — generates stubs for third-party libraries

## Handling Third-Party Libraries
- Many libraries have `py.typed` marker and bundled stubs
- For others, install type stubs: `pip install types-requests`, `types-PyYAML`, etc.
- `typeshed` is the central repo of community-maintained stubs
- Use `# type: ignore` sparingly for truly unresolvable cases

## Incremental mypy Configuration
Start with no strictness flags, then add them one at a time as coverage improves:
1. `--ignore-missing-imports`
2. `--disallow-untyped-defs`
3. `--disallow-any-generics`
4. `--strict`

## Closing Thoughts
Type annotations pay off, but only if adoption is managed pragmatically. Target high-value areas first, use automation to generate a starting point, and increase strictness gradually. Robustness is a journey, not a switch.

# Chapter 6 – Customizing Your Typechecker

## Core Idea
A typechecker is only as useful as its configuration. Tuning your typechecker properly — and understanding alternatives — is what separates a superficial type-annotation pass from **verified documentation** that actively guards your codebase.

## Configuring mypy

### Key Configuration Options (`mypy.ini` or `pyproject.toml`)
| Option | Effect |
|---|---|
| `--strict` | Enables a bundled set of strictness checks, not every possible mypy check; the bundle can change by version |
| `--disallow-untyped-defs` | Require annotations on all functions |
| `--disallow-any-generics` | Forbid bare `list`, `dict` without type params |
| `--warn-return-any` | Warn when returning `Any` from annotated functions |
| `--ignore-missing-imports` | Suppress errors for untyped third-party libraries |
| `--check-untyped-defs` | Typecheck bodies of unannotated functions too |

Start lenient and **incrementally increase strictness** as the codebase gains coverage.

### Mypy Reporting
- `--html-report` / `--txt-report`: generate coverage reports showing what percentage of your code is type-annotated
- Useful for tracking progress when adding annotations to a legacy codebase

### Speeding Up mypy
- **Incremental mode** (default): caches results, only re-checks changed files
- **`dmypy run -- mypy <paths>`**: persistent daemon workflow; speeds up repeated checks on large codebases
- Use `.mypy_cache/` — don't delete it unless debugging

## Alternative Typecheckers

### Pyre (Facebook/Meta)
- Built for large-scale codebases; designed for speed and parallelism
- Integrates with Pysa (Python Static Analyzer) for **security taint analysis**
- `pyre check` for one-shot; `pyre` server for persistent daemon mode
- More opinionated strictness; less configurable than mypy in some areas

### Pyright (Microsoft)
- Powers VS Code's Pylance extension — excellent IDE integration
- Very fast, written in TypeScript
- `pyrightconfig.json` for configuration
- Useful `reportMissingImports`, `reportGeneralTypeIssues` settings
- Good choice if VS Code / Pylance is your primary editor

## Choosing a Typechecker
- **mypy**: most mature, widest community support, most tutorials
- **Pyright**: best VS Code integration and speed
- **Pyre**: best for very large codebases and security analysis
- Mix is fine: run mypy in CI, Pyright in your editor

## Closing Thoughts
Typecheckers are sharpened tools. An unconfigured typechecker misses errors; an over-strict one creates friction. Find the balance that works for your team and gradually increase strictness over time. The investment in configuration pays dividends every time a bug is caught before code review.

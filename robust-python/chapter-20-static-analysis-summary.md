# Chapter 20 – Static Analysis

## Core Idea
**Static analysis** tools inspect your codebase *without running it*, catching errors, style violations, complexity issues, and security vulnerabilities automatically. They are a first line of defense — catching problems before code review, tests, or production.

## What Is Static Analysis?
You've already used one: `mypy` is a static analyzer for types. This chapter covers three more classes:
1. **Linters** — style and common programming mistakes
2. **Complexity checkers** — code that is too hard to understand
3. **Security scanners** — known vulnerability patterns

## 1. Linting with Pylint
Pylint catches:
- PEP 8 style violations
- Dead/unreachable code
- Unused variables and imports
- Access violations (private members accessed externally)
- Missing docstrings
- Class cohesion issues (methods that don't use `self`)
- Common programming errors

```bash
pylint my_module.py
```

### Writing a Custom Pylint Plugin
Pylint is extensible via plugins using its AST visitor interface:
```python
from pylint.checkers import BaseChecker

class MyCustomChecker(BaseChecker):
    name = "my-checker"
    msgs = {
        "W9001": ("Description of the warning", "warning-id", "Long description"),
    }

    def visit_functiondef(self, node):
        # inspect AST nodes and report violations
        ...

def register(linter):
    linter.register_checker(MyCustomChecker(linter))
```
Custom plugins enforce project-specific conventions that generic linters can't know about.

### Other Linters
- **flake8**: lighter than Pylint; fast; highly pluggable
- **ruff**: extremely fast Rust-based linter; drop-in replacement for flake8 + isort + more
- **black**: opinionated auto-formatter — removes style debates entirely

## 2. Complexity Checkers

### Cyclomatic Complexity
Measures the number of independent paths through code. High complexity = hard to understand and test.

**radon** / **flake8-complexity**:
```bash
radon cc my_module.py -s
```
Complexity grades: A (1–5), B (6–10), C (11–20), D (21–30), E (31–40), F (41+). Target A/B where practical; use the metric to prompt investigation rather than as a correctness verdict.

### Cognitive Complexity
A human-oriented metric that accounts for nesting depth and branching in ways cyclomatic complexity doesn't.
- **flake8-cognitive-complexity** plugin

### Halstead Metrics
Measures code volume, vocabulary, difficulty, and effort based on operator/operand counts.
```bash
radon hal my_module.py
```

Rule of thumb: if a function scores badly on complexity metrics, it's a candidate for decomposition.

## 3. Security Analysis

### Bandit
Scans for common security vulnerabilities:
```bash
bandit -r my_package/
```
Checks for:
- Use of `eval()` or `exec()` with untrusted input
- Hardcoded passwords and secrets
- Use of weak cryptographic algorithms (MD5, SHA1)
- SQL injection patterns
- Insecure use of `subprocess` (shell injection)
- HTTP instead of HTTPS

### Safety
Checks installed dependencies against a database of known vulnerabilities:
```bash
safety check
```
Essential in CI: catches vulnerable transitive dependencies.

## Integrating Into CI
Static analysis belongs in your CI pipeline, not just local development:
```yaml
# Example GitHub Actions step
- run: |
    ruff check .
    mypy .
    bandit -r src/
    safety check
```
Gate merges on static analysis passing — no exceptions.

## Closing Thoughts
Static analysis is cheap compared to the bugs it prevents. Linters enforce consistency, complexity checkers identify hard-to-maintain code, and security scanners catch vulnerabilities before they ship. Automate them all in CI and let the tools do the policing.

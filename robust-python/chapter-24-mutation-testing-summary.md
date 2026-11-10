# Chapter 24 – Mutation Testing

## Core Idea
**Mutation testing** measures the *quality* of your tests by deliberately introducing bugs and checking whether your tests catch them. If a bug slips through your test suite undetected, your tests have a hole. Mutation testing finds those holes.

## What Is Mutation Testing?
1. A tool makes a small, targeted change to your source code — a **mutant** (e.g., changes `>` to `>=`)
2. Your test suite runs against the mutant
3. If tests **fail** → the mutant is **killed** ✅ (your tests caught the bug)
4. If tests **pass** → the mutant **survived** ❌ (your tests missed a real bug pattern)

The goal: **kill as many mutants as possible**.

### Example Mutants
Original code:
```python
def is_valid_age(age: int) -> bool:
    return age >= 0 and age <= 150
```
Possible mutants:
- `age >= 0` → `age > 0` (off-by-one on zero)
- `age <= 150` → `age < 150` (off-by-one on 150)
- `and` → `or` (logical operator change)
- `return True` (constant replacement)

If your tests don't cover `age == 0` or `age == 150`, those mutants survive.

## Mutation Testing with mutmut
**Version note:** the reporting and coverage flags below describe older mutmut workflows. Check your installed version's `mutmut --help` and configuration documentation before using `results`, `html`, `--use-coverage`, or `--paths-to-mutate`; newer versions organize these differently.
```bash
pip install mutmut
mutmut run
mutmut results
```

### Reading Results
```
🎉 Killed mutants: 142
🤔 Suspicious mutants: 3
🙁 Survived mutants: 18
```
- **Killed**: tests caught the mutation ✅
- **Survived**: tests missed it — a test gap ❌
- **Suspicious**: interpretation depends on the mutmut version (often unusually slow runs); inspect details rather than assuming a flaky test

A survivor is not automatically a missing test: some mutants are behaviorally equivalent to the original for valid inputs. Distinguish equivalent mutants from meaningful gaps before adding assertions.

### Fixing Surviving Mutants
For each survivor, inspect it:
```bash
mutmut show 42
```
Output shows the mutation. Write a test that would catch it:
```python
def test_age_boundary_zero():
    assert is_valid_age(0) == True

def test_age_boundary_150():
    assert is_valid_age(150) == True

def test_age_above_max():
    assert is_valid_age(151) == False
```

### Mutation Testing Reports
Integrate with coverage reports:
```bash
mutmut run --use-coverage
```
Focuses mutation on lines actually covered — avoids wasting time on dead code.

HTML reports:
```bash
mutmut html
```

## The Fallacy of Coverage Metrics
Code coverage (line/branch coverage) is commonly misused:
- **Coverage measures what was executed** — not whether the test actually *verified* anything
- 100% coverage with useless assertions (`assert True`) means nothing
- A test can execute a line and make no assertion about its behavior

Mutation testing exposes this: a line may be "covered" but a mutation on it survives because no assertion checks its effect.

> Coverage answers "was this code run?"  
> Mutation testing answers "would a test fail if this code were wrong?"

### Combining Coverage and Mutation Testing
Use both:
1. **Coverage** to find untested code paths (cheap, fast)
2. **Mutation testing** to find weakly tested code paths (expensive, slow — run less frequently)

## Adopting Mutation Testing
Mutation testing is slow — runs the full test suite for every mutant. Practical adoption:
- Run on **CI weekly**, not every commit
- Target **critical modules** first (billing, auth, data processing)
- Use `--paths-to-mutate` to scope mutation to high-risk code
- Track mutation score over time as a quality metric alongside coverage

## Closing Thoughts
Mutation testing is the most rigorous way to evaluate test quality. It answers the question: "If a developer accidentally introduces a bug here, will the tests catch it?" High mutation scores mean your safety net is strong and trustworthy. Pair it with coverage, property-based testing, and static analysis for a comprehensive quality strategy.

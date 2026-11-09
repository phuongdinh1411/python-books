# Chapter 21 – Testing Strategy

## Core Idea
Tests are your most important safety net — but only if they're the right tests, written the right way. Without a strategy, tests become a burden rather than a benefit. This chapter is about **choosing what to test, how to write tests economically, and Python-specific best practices**.

## Defining Your Test Strategy
A test strategy is a deliberate plan for spending testing effort to mitigate risk. It answers:
- What questions does this system need to answer?
- What tests will answer those questions?
- How often should those tests run?
- Who is responsible for writing them?

Example strategy questions:
- Does the system function as expected? → Unit + acceptance tests, run daily
- Will it perform under load? → Performance tests, run weekly
- Is it secure? → Security audits, ongoing

Every team's strategy will differ — tailor it to your risk profile.

## What Is a Test?
A test is an executable specification: it defines **expected behavior** and verifies it automatically. Good tests:
- Are deterministic (same result every run)
- Are independent (don't rely on run order or shared state)
- Are fast (slow tests get skipped)
- Have a single reason to fail (easy to diagnose)

### Test Pyramid
```
        /\
       /  \  ← E2E / Acceptance (few, slow, high-confidence)
      /    \
     /      \  ← Integration (moderate)
    /        \
   /          \  ← Unit (many, fast, targeted)
  /____________\
```
Invest heavily in unit tests, moderately in integration, sparingly in E2E.

## Reducing Test Cost

### AAA Testing (Arrange, Act, Assert)
A consistent structure reduces cognitive load:
```python
def test_apply_discount():
    # Arrange
    menu_item = MenuItem(name="Burger", price=10.00)
    discount = Discount(percentage=0.10)

    # Act
    discounted = apply_discount(menu_item, discount)

    # Assert
    assert discounted.price == 9.00
```
- **Arrange**: set up the system under test and its dependencies
- **Act**: invoke the behavior being tested
- **Assert**: verify the outcome

Keep each section small. If Arrange is huge, your code may need dependency injection. If Assert is huge, the test may be doing too much.

### Test Doubles
Replace real dependencies with controlled stand-ins:

| Double | Purpose |
|---|---|
| **Stub** | Returns pre-defined values |
| **Mock** | Records calls; asserts interactions |
| **Fake** | Simplified working implementation (in-memory DB) |
| **Spy** | Records calls but still executes real code |

Python's `unittest.mock` / `pytest-mock`:
```python
def test_notify_on_order(mocker):
    mock_notifier = mocker.Mock(spec=Notifier)
    processor = OrderProcessor(mock_notifier)

    processor.process(order)

    mock_notifier.send.assert_called_once_with("Order confirmed")
```

### pytest Best Practices
- Use **fixtures** (`@pytest.fixture`) for reusable setup/teardown
- Use **parametrize** (`@pytest.mark.parametrize`) to run the same test with multiple inputs
- Keep fixtures small and focused
- Use `conftest.py` for shared fixtures
- Name tests clearly: `test_<what>_when_<condition>_returns_<expected>`

### What NOT to Test
- Private implementation details (test behavior, not internals)
- Third-party library code
- Generated code (auto-generated migrations, etc.)
- Simple attribute accessors with no logic

## Closing Thoughts
A thoughtful test strategy saves time by focusing effort where it matters most. Write tests that give confidence proportional to their cost. Well-structured, deterministic tests written in the AAA pattern become assets; poorly organized tests become liabilities.

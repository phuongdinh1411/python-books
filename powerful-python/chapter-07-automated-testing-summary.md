# Chapter 7 – Automated Testing

## Core Idea
**Automated testing** is a superpower that lets you build more complex software, refactor safely, and stay in a productive flow state. **Test-Driven Development (TDD)** — writing the test first — is the fastest way to develop this skill.

## Key Concepts

### What Is TDD?
- Write the **test first**, run it to confirm it **fails**, then write the code to make it pass
- Forces you to think about interfaces and correctness upfront
- Enables safe, large-scale refactoring with confidence
- Builds **cognitive flow** — a highly productive, focused state

### Structure of a `unittest` Test
```python
import unittest
from angles import Angle

class TestAngle(unittest.TestCase):
    def test_degrees(self):
        a = Angle(60)
        self.assertEqual(60, a.degrees)
        self.assertTrue(a.is_acute())

    def test_arithmetic(self):
        total = Angle(60) + Angle(320)
        self.assertEqual(20, total.degrees, 'Adding angles with wrap-around')
```
- Class must subclass `unittest.TestCase`
- Test method names **must start with `test`**
- Run with: `python -m unittest test_angles.py`

### Common Assertion Methods
| Method | Checks |
|---|---|
| `assertEqual(expected, actual)` | Values are equal |
| `assertNotEqual(a, b)` | Values differ |
| `assertTrue(expr)` | Expression is truthy |
| `assertFalse(expr)` | Expression is falsy |
| `assertRaises(ExcType)` | Code raises that exception |
| `assertIn(item, container)` | Item is in container |
| `assertIsInstance(obj, cls)` | Object is an instance |

Always put **expected value first** in `assertEqual` — stay consistent across your codebase.

### `setUp` and `tearDown` — Test Fixtures
- `setUp()` runs **before each test method** — creates a fresh, consistent test environment
- `tearDown()` runs **after each test method** — cleans up (files, connections, etc.)
```python
class TestState(unittest.TestCase):
    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # create temp files, objects...

    def tearDown(self):
        shutil.rmtree(self.testdir)  # always runs, even if assertions fail

    def test_change_value(self):
        self.state.data["foo"] = 21
        self.state.close()
        reloaded = State(self.state_file_path)
        self.assertEqual(21, reloaded.data["foo"])
```
- `tearDown` runs even if an assertion fails — good for guaranteed cleanup
- Spelling matters: `setUp` / `tearDown`, not `setup` / `teardown`

### Asserting Exceptions
```python
def test_roman2int_error(self):
    with self.assertRaises(ValueError):
        roman2int("This is not a valid roman numeral.")
```

### Subtests — Running All Cases, Not Stopping at First Failure
A plain `for` loop stops at the first failure and hides which input caused it. Use `subTest` instead:
```python
def test_whitespace(self):
    texts = ["foo bar", "   foo bar", "foo\tbar", "foo   bar"]
    for text in texts:
        with self.subTest(text=text):
            self.assertEqual(2, numwords(text))
```
- All inputs are tested, failures are **all reported** with the specific failing value
- Pass any key-value pairs to `subTest()` — they appear in the failure output
- Equivalent to pytest's **parameterized tests**

### Test Organization Tips
- One `TestCase` subclass per class under test
- Multiple test methods for different aspects of behavior
- Test methods are **independent** — don't rely on execution order
- Each test method should be **self-contained** (use `setUp` for shared state)

### When to Use TDD vs. Not
- TDD works best when you have **clear design clarity** on interfaces and architecture
- Less useful in exploratory/research phases where the design is still evolving
- Even if you don't always do TDD, practice it strictly for a period to build the skill

## Key Takeaways
- Always run the test first to **confirm it fails** — this validates the test itself
- `setUp` / `tearDown` create a clean sandbox per test; `tearDown` always runs
- Use `assertRaises` inside a `with` block to test exception-raising behavior
- Use `subTest` to test multiple inputs without stopping at the first failure
- TDD's greatest benefit is **cognitive** — it helps you stay focused and builds correct code incrementally

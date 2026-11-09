# Chapter 9 – Testing and Debugging

## Core Idea
Python's dynamic nature makes runtime errors possible even when code "looks right." Tests are your insurance policy — they give confidence, catch regressions, and make refactoring safe. Python's standard library and dynamic features make writing tests and debugging surprisingly easy.

## Items Summary

### Item 75: Use `repr` Strings for Debugging Output
- `print(value)` calls `str()` — often ambiguous: `print("5")` and `print(5)` look the same
- `repr()` produces an unambiguous, machine-readable representation:
  ```python
  print(repr("hello"))   # 'hello'  (quotes included)
  print(repr(5))         # 5
  print(repr(5.0))       # 5.0
  ```
- In `__repr__`, return a string that, if `eval()`-ed, would recreate the object:
  ```python
  class Point:
      def __repr__(self):
          return f"Point({self.x!r}, {self.y!r})"
  ```
- Use `f"{value!r}"` in f-strings to get the `repr` form
- Always implement `__repr__` on custom classes — makes debugging 10× easier

### Item 76: Verify Related Behaviors in `TestCase` Subclasses
- Use `unittest.TestCase` to group related test methods:
  ```python
  class TestMyFunction(unittest.TestCase):
      def test_basic(self):
          self.assertEqual(add(2, 3), 5)

      def test_negative(self):
          self.assertEqual(add(-1, -1), -2)

      def test_raises(self):
          with self.assertRaises(ValueError):
              add("a", 1)
  ```
- Key assertions: `assertEqual`, `assertNotEqual`, `assertTrue`, `assertFalse`, `assertIs`, `assertIsNone`, `assertIn`, `assertRaises`, `assertAlmostEqual`
- Group tests by the unit they test — one `TestCase` subclass per module or class
- `pytest` can discover and run `unittest.TestCase` subclasses automatically

### Item 77: Isolate Tests from Each Other with `setUp`, `tearDown`, `setUpModule`, and `tearDownModule`
- Each test method should be independent — shared state between tests causes order-dependent failures
- **`setUp(self)`**: runs before each test method — create fresh state
- **`tearDown(self)`**: runs after each test method — clean up (even if test fails)
- **`setUpModule()`**: module-level setup, runs once before all tests in the file
- **`tearDownModule()`**: module-level teardown, runs once after all tests
- Use `setUp`/`tearDown` for: creating temp files, opening DB connections, initializing mocks
- Tests with clean setup are deterministic and order-independent

### Item 78: Use Mocks to Test Code with Complex Dependencies
- A **mock** replaces a real dependency with a controlled stand-in that records calls and returns configured values
- Use `unittest.mock.Mock` and `unittest.mock.patch`:
  ```python
  from unittest.mock import Mock, patch

  def test_send_email():
      with patch("my_module.send_smtp") as mock_smtp:
          mock_smtp.return_value = True
          result = notify_user("alice@example.com", "Hello")
          mock_smtp.assert_called_once_with("alice@example.com", "Hello")
          assert result is True
  ```
- `patch` replaces the named object only within the `with` block — restored afterward
- `Mock(spec=RealClass)` creates a mock that mirrors the real interface — catches typos in method names
- Mock sparingly — overmocking leads to tests that pass even when real integrations break

### Item 79: Encapsulate Dependencies to Facilitate Mocking and Testing
- Code that directly instantiates dependencies is hard to test:
  ```python
  # Hard to test
  class EmailSender:
      def send(self, to, msg):
          smtp = smtplib.SMTP("mail.example.com")  # hard-coded
          ...
  ```
- Inject dependencies instead — pass them in, don't create them internally:
  ```python
  class EmailSender:
      def __init__(self, smtp_factory=smtplib.SMTP):
          self._smtp_factory = smtp_factory

      def send(self, to, msg):
          smtp = self._smtp_factory("mail.example.com")
  ```
- In tests, inject a mock factory; in production, use the real one
- This pattern (dependency injection) is the key to testable code

### Item 80: Consider Interactive Debugging with `pdb`
- Drop into the Python debugger at any point:
  ```python
  import pdb; pdb.set_trace()    # Python < 3.7
  breakpoint()                    # Python 3.7+ (preferred)
  ```
- Key `pdb` commands:
  | Command | Action |
  |---|---|
  | `n` (next) | Execute next line |
  | `s` (step) | Step into function call |
  | `c` (continue) | Run until next breakpoint |
  | `l` (list) | Show surrounding source |
  | `p expr` | Print expression value |
  | `pp expr` | Pretty-print expression |
  | `b lineno` | Set breakpoint |
  | `q` (quit) | Exit debugger |
  | `w` (where) | Show call stack |
- Post-mortem debugging: `python -m pdb -c continue my_script.py` or `pdb.pm()` after an exception
- Better alternatives: `ipdb` (IPython-enhanced), VS Code / PyCharm integrated debuggers

### Item 81: Use `tracemalloc` to Understand Memory Usage and Leaks
- Python has a garbage collector, but memory leaks still occur (lingering references, caches, circular refs)
- `tracemalloc` traces memory allocations to find the source:
  ```python
  import tracemalloc

  tracemalloc.start()
  # ... run your code ...
  snapshot = tracemalloc.take_snapshot()
  top_stats = snapshot.statistics("lineno")
  for stat in top_stats[:10]:
      print(stat)
  ```
- Compare two snapshots to find what grew:
  ```python
  snapshot2 = tracemalloc.take_snapshot()
  stats = snapshot2.compare_to(snapshot1, "lineno")
  ```
- Output shows file/line and size of allocations — pinpoints exactly where memory is being allocated

## Key Takeaways
- Implement `__repr__` on all custom classes — it pays for itself the first time you debug
- Group related tests in `TestCase` subclasses; use `setUp`/`tearDown` for isolation
- Use `Mock` and `patch` to replace dependencies in tests — but keep mocking targeted
- Inject dependencies rather than hard-coding them — this is the key to testable design
- Use `breakpoint()` for quick interactive debugging
- Use `tracemalloc` to find memory leaks and unexpected allocation hotspots

# Chapter 3 – Functions

## Core Idea
Functions are Python's primary building block for organizing code. Python gives functions unique capabilities — closures, variadic arguments, keyword-only parameters — that, when used well, make APIs clearer and safer. Used poorly, they introduce subtle, hard-to-find bugs.

## Items Summary

### Item 19: Never Unpack More Than Three Variables When Functions Return Multiple Values
- Python allows returning multiple values via implicit tuples: `return min_val, max_val`
- Temptation: return 4, 5, 6 values to avoid creating a class
- **Rule**: never unpack more than three variables from a return
- Beyond three: create a small class or `dataclass` instead — it names things and prevents ordering mistakes

### Item 20: Prefer Raising Exceptions to Returning `None`
- Returning `None` to signal error is dangerous because `None` is falsy — just like `0`, `""`, `[]`
  ```python
  # Bug trap: an API returning None for failure is easy to confuse with valid 0.0
  result = divide(0, 5)
  if not result:  # wrongly triggers for valid result of 0.0
      print("error")
  ```
- Instead, **raise an exception** on error conditions:
  ```python
  def divide(a, b):
      if b == 0:
          raise ValueError("Cannot divide by zero")
      return a / b
  ```
- Exceptions propagate if not handled; callers can catch specific errors at a deliberate recovery boundary

### Item 21: Know How Closures Interact with Variable Scope
- Inner functions can *read* variables from enclosing scopes (closure)
- But to *assign* to an enclosing scope variable, you need `nonlocal`:
  ```python
  def make_counter():
      count = 0
      def increment():
          nonlocal count  # required to rebind, not just read
          count += 1
          return count
      return increment
  ```
- LEGB rule: Local → Enclosing → Global → Built-in
- `global` for module-level rebinding; `nonlocal` for enclosing function scope
- Avoid `global` and `nonlocal` in complex code — they make reasoning about state hard

### Item 22: Reduce Visual Noise with Variable Positional Arguments (`*args`)
- `*args` accepts any number of positional arguments:
  ```python
  def log(message, *values):
      print(message, values)
  ```
- Use when a function legitimately takes a variable number of same-type arguments
- **Caution**: passing a generator to `*args` will exhaust it into memory immediately — problematic for large inputs
- Don't insert a new positional parameter *before* existing `*args` — it may silently consume an argument previously captured there. Parameters *after* `*args` are already keyword-only.

### Item 23: Provide Optional Behavior with Keyword Arguments
- Ordinary positional-or-keyword parameters can be passed by keyword: `divide(a=10, b=2)`. Positional-only parameters (see Item 25) cannot.
- Keyword arguments provide self-documenting call sites
- Use default values to make parameters optional:
  ```python
  def flow_rate(weight_diff, time_diff, period=1, units_per_kg=1):
      ...
  ```
- **Best practice**: add new optional parameters as keyword arguments with defaults — backward compatible

### Item 24: Use `None` and Docstrings to Specify Dynamic Default Arguments
- **The mutable default trap**:
  ```python
  def log(message, when=datetime.now()):  # BUG: evaluated once at definition
      print(f"{when}: {message}")
  ```
- Use `None` as the default and create the value inside the function:
  ```python
  def log(message, when=None):
      if when is None:
          when = datetime.now()
      print(f"{when}: {message}")
  ```
- Document the dynamic default behavior in the docstring

### Item 25: Enforce Clarity with Keyword-Only and Positional-Only Arguments
- **Keyword-only** (after `*` or `*args`): callers *must* use keyword syntax
  ```python
  def safe_division(number, divisor, *, ignore_overflow=False):
      ...
  safe_division(1, 0, ignore_overflow=True)  # required keyword
  ```
- **Positional-only** (before `/`, Python 3.8+): callers *must not* use keyword syntax
  ```python
  def safe_division(number, divisor, /, *, ignore_overflow=False):
      ...
  ```
- Positional-only lets you rename parameters without breaking callers
- Combine both for APIs where some args are flexible, some are fixed

### Item 26: Define Function Decorators with `functools.wraps`
- Decorators wrap a function to add behavior (logging, retry, timing)
- Without `functools.wraps`, the wrapper hides the original function's metadata:
  ```python
  from functools import wraps

  def my_decorator(func):
      @wraps(func)  # preserves __name__, __doc__, __module__, etc.
      def wrapper(*args, **kwargs):
          # ... pre/post logic ...
          return func(*args, **kwargs)
      return wrapper
  ```
- Always use `@wraps(func)` in decorators — it preserves introspection, debugging, and documentation

## Key Takeaways
- Keep multi-return functions to ≤3 unpacked values; use classes for more
- Raise exceptions rather than returning `None` for errors
- Use keyword-only args (`*`) for boolean flags and optional parameters to prevent positional confusion
- Always default mutable/dynamic arguments to `None`
- Use `@functools.wraps` in every decorator

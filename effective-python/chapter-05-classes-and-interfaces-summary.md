# Chapter 5 – Classes and Interfaces

## Core Idea
Python's class system is flexible and powerful, but that flexibility makes it easy to over-engineer or misapply OOP patterns. This chapter covers when and how to use classes, inheritance, mixins, and the `collections.abc` module to write clean, maintainable object-oriented code.

## Items Summary

### Item 37: Compose Classes Instead of Nesting Many Levels of Built-in Types
- Using nested `dict`s and `tuple`s for complex data becomes unreadable quickly:
  ```python
  # Hard to understand
  grades[student][subject] = (score, weight)
  ```
- **Rule**: when a data container grows to two or more levels of nesting, refactor into classes
  ```python
  @dataclass
  class Grade:
      score: float
      weight: float

  @dataclass
  class Subject:
      name: str
      grades: list[Grade] = field(default_factory=list)
  ```
- Named classes document intent and allow methods that enforce invariants

### Item 38: Accept Functions Instead of Classes for Simple Interfaces
- Many Python APIs accept callable hooks (e.g., `sort(key=...)`, `defaultdict(factory)`)
- For simple interfaces, pass a function — no need to create a class:
  ```python
  names.sort(key=lambda x: x.lower())
  ```
- When state is needed across calls, use a class with `__call__`:
  ```python
  class CountMissing:
      def __init__(self):
          self.added = 0
      def __call__(self):
          self.added += 1
          return 0

  counter = CountMissing()
  result = defaultdict(counter)
  ```
- `__call__` makes instances callable like functions while retaining state

### Item 39: Use `@classmethod` Polymorphism to Construct Objects Generically
- `@classmethod` receives the class as first argument (`cls`), enabling subclass-aware construction:
  ```python
  class InputData:
      @classmethod
      def generate_inputs(cls, config):
          raise NotImplementedError

  class PathInputData(InputData):
      @classmethod
      def generate_inputs(cls, config):
          return [cls(path) for path in config["paths"]]
  ```
- Enables factory methods that work polymorphically without `isinstance` checks
- Use instead of `__init__` overloads for multiple construction patterns

### Item 40: Initialize Parent Classes with `super()`
- Never call the parent class `__init__` directly: `Parent.__init__(self)` breaks with multiple inheritance (diamond problem)
- Always use `super()`:
  ```python
  class Child(Parent):
      def __init__(self):
          super().__init__()  # correct
  ```
- `super()` follows Python's **Method Resolution Order (MRO)**. A diamond hierarchy initializes cooperatively only if participating methods call `super()` consistently and accept compatible arguments.
- `super()` without arguments (Python 3) is equivalent to `super(Child, self)` but less error-prone

### Item 41: Consider Composing Functionality with Mix-in Classes
- A **mix-in** is a class that provides reusable methods but no instance state
- Mix-ins are composed via multiple inheritance without the problems of deep hierarchies:
  ```python
  class JsonMixin:
      def to_json(self):
          return json.dumps(self.__dict__)

  class LogMixin:
      def log(self, msg):
          print(f"[{self.__class__.__name__}] {msg}")

  class MyModel(JsonMixin, LogMixin):
      def __init__(self, name):
          self.name = name
  ```
- Make mix-ins independent (no `__init__`, no instance state) to avoid MRO conflicts
- Compose multiple mix-ins rather than building deep single-inheritance trees

### Item 42: Prefer Public Attributes Over Private Ones
- Python name-mangling: `__attr` becomes `_ClassName__attr` — it's not truly private
- **Private attributes are not enforced by the runtime** — only a convention
- Overusing `__private` breaks subclass access and creates friction
- Prefer `_single_leading_underscore` ("internal, not part of public API") over `__double`
- Use `__double` only to prevent accidental name clashes in complex inheritance hierarchies
- Document what should and shouldn't be used, rather than enforcing it with mangling

### Item 43: Inherit from `collections.abc` for Custom Container Types
- When building custom container classes, don't implement everything from scratch
- `collections.abc` provides abstract base classes with implementations of derived methods:
  ```python
  from collections.abc import MutableSequence

  class ListWrapper(MutableSequence):
      def __init__(self): self._data = []
      def __getitem__(self, i): return self._data[i]
      def __setitem__(self, i, v): self._data[i] = v
      def __delitem__(self, i): del self._data[i]
      def __len__(self): return len(self._data)
      def insert(self, i, v): self._data.insert(i, v)
  ```
- Implementing the abstract methods gets you `append`, `extend`, `pop`, `remove`, `count`, `index` for free
- ABC mixins supply derived methods, not proof of correct semantics. For example, automatically sorting after `insert(i, v)` would violate the usual positional `MutableSequence` contract.
- Important ABCs: `Sequence`, `MutableSequence`, `Mapping`, `MutableMapping`, `Set`, `Iterator`

## Key Takeaways
- Break deeply nested built-in types into named classes early
- Use `__call__` for stateful callables; prefer functions for stateless hooks
- Always use `super()` in `__init__` — never direct parent calls
- Mix-ins over deep inheritance; compose behavior horizontally
- Prefer `_protected` over `__private` for internal attributes
- Subclass `collections.abc` for custom containers to get correct behavior for free

# Chapter 6 – Metaclasses and Attributes

## Core Idea
Python's metaclass and dynamic attribute systems allow you to intercept class creation and attribute access at a deep level. These tools power many frameworks (Django ORM, dataclasses, attrs). Used with the **principle of least surprise**, they're powerful; used carelessly, they produce incomprehensible code.

## Items Summary

### Item 44: Use Plain Attributes Instead of Setter and Getter Methods
- Java-style getters/setters are **not Pythonic**:
  ```python
  # Bad (Java style)
  r.set_ohms(r.get_ohms() + 1000)

  # Good (Python style)
  r.ohms += 1000
  ```
- Start with simple public attributes — you can always add `@property` later without changing the API
- Python's `@property` means you never need to pre-emptively wrap everything in getters/setters "just in case"

### Item 45: Consider `@property` Instead of Refactoring Attributes
- `@property` adds computed or validated behavior to an attribute access without changing the calling code:
  ```python
  class Battery:
      def __init__(self, capacity):
          self._capacity = capacity
          self._charge = 0

      @property
      def charge_fraction(self):
          return self._charge / self._capacity

      @charge_fraction.setter
      def charge_fraction(self, value):
          if not 0 <= value <= 1:
              raise ValueError("Fraction must be 0..1")
          self._charge = value * self._capacity
  ```
- Ideal for migrating from simple attributes to validated/computed ones with zero caller changes
- **Warning**: avoid side effects in `@property` getters — they violate the principle of least surprise

### Item 46: Use Descriptors for Reusable `@property` Methods
- `@property` is per-class — can't be shared across multiple attributes or classes
- **Descriptors** implement `__get__`, `__set__`, `__delete__` and can be reused:
  ```python
  class Validated:
      def __set_name__(self, owner, name):
          self.name = name

      def __get__(self, obj, objtype=None):
          if obj is None:
              return self
          return getattr(obj, f"_{self.name}", None)

      def __set__(self, obj, value):
          if not isinstance(value, (int, float)):
              raise TypeError(f"{self.name} must be numeric")
          setattr(obj, f"_{self.name}", value)

  class Grade:
      score = Validated()
      weight = Validated()
  ```
- Use descriptors when the same validation/logic needs to apply to multiple class attributes

### Item 47: Use `__getattr__`, `__getattribute__`, and `__setattr__` for Lazy Attributes
- `__getattr__(self, name)`: called only when normal attribute lookup fails — use for **lazy loading**:
  ```python
  class LazyDB:
      def __getattr__(self, name):
          value = self._load(name)  # load on first access
          setattr(self, name, value)
          return value
  ```
- `__getattribute__(self, name)`: called on **every** attribute access — extremely powerful but dangerous (infinite recursion risk)
  - Must call `super().__getattribute__(name)` to actually get the value
- `__setattr__(self, name, value)`: called on every attribute assignment — useful for logging, validation, or proxy objects
- Avoid `__getattribute__` unless you truly need to intercept every access

### Item 48: Validate Subclasses with `__init_subclass__`
- Classic `__init_subclass__` validates subclass definitions at **class creation time**, before any instance is created:
  ```python
  class Polygon:
      def __init_subclass__(cls, sides, **kwargs):
          super().__init_subclass__(**kwargs)
          if sides < 3:
              raise ValueError("Polygon needs >= 3 sides")
          cls.sides = sides

  class Triangle(Polygon, sides=3): pass   # OK
  class Line(Polygon, sides=2): pass       # Raises ValueError
  ```
- Prefer `__init_subclass__` over metaclasses for subclass validation — cleaner and composable

### Item 49: Register Class Existence with `__init_subclass__`
- Use `__init_subclass__` to auto-register subclasses in a global registry — enables plugin patterns:
  ```python
  registry = {}

  class Base:
      def __init_subclass__(cls, **kwargs):
          super().__init_subclass__(**kwargs)
          registry[cls.__name__] = cls

  class Dog(Base): pass
  class Cat(Base): pass

  print(registry)  # {'Dog': <class 'Dog'>, 'Cat': <class 'Cat'>}
  ```
- Eliminates the need for manual registration calls; works automatically on subclass definition
- Useful for serialization, plugin systems, command registries

### Item 50: Annotate Class Attributes with `__set_name__`
- Descriptors don't know their own attribute name — `__set_name__` tells them:
  ```python
  class Field:
      def __set_name__(self, owner, name):
          self.name = name
          self.internal = f"_{name}"

      def __get__(self, obj, objtype=None):
          return getattr(obj, self.internal, None)

      def __set__(self, obj, value):
          setattr(obj, self.internal, value)

  class Customer:
      first_name = Field()
      last_name = Field()
  ```
- Called automatically when the class is defined; `owner` = the class, `name` = attribute name
- This is how `dataclasses` and similar libraries inspect and name fields

### Item 51: Prefer Class Decorators Over Metaclasses for Composable Class Extensions
- **Metaclasses**: powerful but hard to compose (only one metaclass per class); confusing syntax
- **Class decorators**: just a function that takes a class and returns a modified class — simple and composable:
  ```python
  def add_logging(cls):
      original_init = cls.__init__
      def new_init(self, *args, **kwargs):
          print(f"Creating {cls.__name__}")
          original_init(self, *args, **kwargs)
      cls.__init__ = new_init
      return cls

  @add_logging
  class MyClass:
      def __init__(self, x):
          self.x = x
  ```
- Multiple class decorators can be stacked; metaclass conflicts are nearly impossible to resolve
- Use class decorators for most class extension needs; reserve metaclasses for framework-level infrastructure

## Key Takeaways
- Start with plain attributes; upgrade to `@property` only when needed
- Use descriptors to share property logic across attributes/classes
- Use `__getattr__` for lazy loading; avoid `__getattribute__` unless necessary
- `__init_subclass__` is the modern, composable way to validate/register subclasses
- Prefer class decorators over metaclasses — they're simpler and composable

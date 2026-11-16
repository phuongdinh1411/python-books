# Chapter 23 – Attribute Descriptors

## Core Idea
A **descriptor** is a class that defines `__get__`, `__set__`, or `__delete__` and is assigned to a **class attribute**. Descriptors power properties, methods, class methods, static methods, and `__slots__` — they are the underlying machinery of Python's attribute access protocol.

## What a Descriptor Is
```python
class Validator:
    def __set_name__(self, owner, name):   # called when class is created
        self.storage_name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self             # accessed from class, return descriptor
        return instance.__dict__.get(self.storage_name, 0)

    def __set__(self, instance, value):
        if value <= 0:
            raise ValueError(f'{self.storage_name} must be > 0')
        instance.__dict__[self.storage_name] = value

class LineItem:
    quantity = Validator()    # descriptor instance assigned as class attribute
    price = Validator()

item = LineItem()
item.quantity = 5    # triggers Validator.__set__
item.quantity        # triggers Validator.__get__
```

## Overriding vs Non-Overriding Descriptors

| Type | Methods | Behaviour |
|---|---|---|
| **Overriding** (data descriptor) | `__get__` + `__set__` (or `__delete__`) | Class-level descriptor takes priority over instance `__dict__` |
| **Overriding without `__get__`** | `__set__` only | Class-level for writes; instance `__dict__` for reads |
| **Non-overriding** | `__get__` only | Instance `__dict__` takes priority; instance attribute shadows it |

```python
# Non-overriding: instance attribute CAN shadow the descriptor
class NonOverride:
    def __get__(self, instance, owner):
        return 'descriptor'

class C:
    x = NonOverride()

obj = C()
obj.x         # 'descriptor'  — calls __get__
obj.x = 7     # sets instance __dict__['x'] = 7
obj.x         # 7             — instance attr shadows descriptor
```

## Methods Are Descriptors
Regular functions are non-overriding descriptors. `obj.method` triggers `function.__get__(obj, type(obj))`, which returns a **bound method** that prepends `obj` as the first argument:
```python
class C:
    def spam(self):
        pass

C.spam             # <function C.spam at ...>
C().spam           # <bound method C.spam of <C object>>
C.spam.__get__(C(), C)  # same as C().spam
```
This is why methods work: the function descriptor binds `self` automatically.

## `__set_name__`
Called by `type.__new__` during class creation — lets descriptors know their attribute name without manual configuration:
```python
class Validated:
    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = '_' + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, self.validate(value))

    def validate(self, value): ...
```

## Descriptor Usage Tips
1. **Validation descriptors**: use `__set__` only — store validated value directly in instance `__dict__` for fast reads
2. **Caching descriptors**: use `__get__` only (non-overriding) — cache by setting same-name attribute on instance, which then shadows the descriptor
3. **Read-only descriptors**: implement both `__get__` AND `__set__` (raise `AttributeError` in `__set__`)
4. **Don't shadow non-special methods**: functions and methods are non-overriding; `obj.method = 7` will shadow the method for that instance

## `functools.cached_property` Is a Non-Overriding Descriptor
It implements `__get__` only. On first access it computes the value, stores it in the instance `__dict__`, and subsequent accesses hit `__dict__` directly — without calling `__get__` again.

## Closing Thoughts
Descriptors are the unified mechanism behind properties, functions, class methods, static methods, and `__slots__`. Understanding them demystifies Python's attribute lookup. The key practical guideline: use overriding descriptors (data descriptors) for validation, use non-overriding descriptors for computed or cached attributes, and always implement both `__get__` and `__set__` for read-only attributes to prevent silent shadowing.

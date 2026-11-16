# Chapter 14 – Inheritance: For Better or for Worse

## Core Idea
Inheritance is often overused. Python's `super()` and MRO make multiple inheritance workable, but the best guide is: **favour composition over inheritance**, and use mixins and ABCs rather than deep concrete hierarchies.

## `super()` and the MRO
```python
class C(B):
    def method(self):
        super().method()   # delegates to next in MRO, not necessarily B directly
```
The **Method Resolution Order (MRO)** is computed by the C3 linearisation algorithm:
```python
D.__mro__   # (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)
```
Always call `super()` in cooperative multiple inheritance — it forwards the call through the entire MRO chain.

## Subclassing Built-Ins Is Tricky
Python built-ins (list, dict, str) are implemented in C and **do not call overridden methods** from Python subclasses in all situations:
```python
class MyDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value * 2)

d = MyDict(a=1)   # __init__ calls C code directly, bypasses our __setitem__
d['a']            # 1, not 2!
```
Subclass `UserDict`, `UserList`, `UserString` from `collections` instead — they are implemented in Python and properly delegate.

## Multiple Inheritance and MRO

```python
class A:
    def ping(self): print('A')

class B(A):
    def ping(self): print('B'); super().ping()

class C(A):
    def ping(self): print('C'); super().ping()

class D(B, C):
    def ping(self): print('D'); super().ping()

D().ping()   # D, B, C, A  — follows MRO order
```

## Mixin Classes
A mixin provides methods for reuse without representing an "is-a" relationship:
- Should not be instantiated directly
- Should not have a primary `__init__`
- Typically overrides or adds a few specific methods
- Name conventionally with `Mixin` suffix

```python
class CaseInsensitiveMixin:
    def __contains__(self, key):
        return key.upper() in {k.upper() for k in self}
```

## Real-World Multiple Inheritance
Django generic class-based views use mixins extensively:
- `TemplateResponseMixin` → provides `render_to_response`
- `ContextMixin` → provides `get_context_data`
- `View` → provides `dispatch`
- `TemplateView(TemplateResponseMixin, ContextMixin, View)` → assembles them

Tkinter is a cautionary example: deep mixed hierarchies without clear roles, a class named `Misc` with 100+ methods that all widgets inherit — a design that should be split into focused mixins.

## Guidelines for Coping with Inheritance
1. **Favour composition over inheritance** — consider whether a `has-a` relationship better models reality than `is-a`
2. **Use ABCs for explicit interface contracts** — makes the required protocol visible
3. **Use mixins for code reuse** — keep them small and focused, name them `*Mixin`
4. **Provide aggregate classes** — one class that inherits from multiple ABCs/mixins for user convenience
5. **Only subclass classes designed for subclassing** — check the docs; classes not intended for subclassing often have internal state that breaks
6. **Avoid subclassing concrete classes** — internal state can easily be corrupted when methods are overridden

> "All non-leaf classes should be abstract." — Scott Meyers, *More Effective C++*

## Closing Thoughts
Python's MRO makes multiple inheritance well-defined, but not necessarily simple. The real question is whether inheritance is the right tool at all. Many frameworks that look like they need deep hierarchies work better with composition and small, well-named mixins. The pitfalls of subclassing C built-ins (`dict`, `list`) are a specific gotcha that trips many developers — use `UserDict`/`UserList` when you need to subclass.

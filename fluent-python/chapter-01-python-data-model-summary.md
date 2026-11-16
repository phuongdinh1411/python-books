# Chapter 1 – The Python Data Model

## Core Idea
The Python Data Model is the API that makes objects play well with the language. It formalizes the interfaces for sequences, functions, iterators, coroutines, classes, and context managers through **special methods** (dunder methods), making Python internally consistent and extensible.

## The Data Model as a Framework
Python works like a framework: you write methods that the **interpreter** calls, not your own application code. For example, `obj[key]` triggers `obj.__getitem__(key)`. This means any class can integrate with built-in syntax just by implementing the right dunder methods.

The key insight is that `len(collection)` rather than `collection.len()` is not a quirk — it's the expression of this model. Built-ins like `len`, `iter`, `repr`, `abs`, and operators delegate to special methods.

## Special Methods You Implement
Python invokes special methods in response to:
- **Collections**: `__len__`, `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`
- **Iteration**: `__iter__`, `__next__`, `__reversed__`; async variants `__aiter__`, `__anext__`
- **Operator overloading**: `__add__`, `__mul__`, `__eq__`, `__lt__`, etc.
- **String representation**: `__repr__`, `__str__`, `__format__`, `__bytes__`
- **Boolean/numeric conversion**: `__bool__`, `__int__`, `__float__`, `__hash__`
- **Attribute access**: `__getattr__`, `__setattr__`, `__getattribute__`, `__delattr__`
- **Context managers**: `__enter__`, `__exit__`; async: `__aenter__`, `__aexit__`
- **Callable objects**: `__call__`
- **Object lifecycle**: `__new__`, `__init__`, `__del__`
- **Class metaprogramming**: `__init_subclass__`, `__class_getitem__`

## A Pythonic Card Deck Example
By implementing just `__len__` and `__getitem__`, a custom `FrenchDeck` class can:
- Return its length via `len(deck)`
- Be indexed and sliced: `deck[0]`, `deck[-1]`, `deck[::2]`
- Be iterated with `for card in deck`
- Be sorted with `sorted(deck, key=spades_high)`
- Support `random.choice(deck)` and `random.shuffle(deck)` (with `__setitem__`)

All that from just two methods — by delegating to Python's built-in machinery.

## Why `len` Is Not a Method
`len` is a built-in that directly reads `ob_size` from C structs for built-in types — it's a constant-time O(1) operation that avoids a method call overhead. The special method `__len__` is still invoked when `len()` is called on user-defined types. This is a pragmatic concession to speed, documented explicitly in the data model.

## The Collection ABC
`collections.abc.Collection` requires three abstract methods:
- `__len__` → `Sized`
- `__iter__` → `Iterable`
- `__contains__` → `Container`

Three important specializations:
- `Sequence` (list, str) — reversible, ordered
- `Mapping` (dict) — key→value lookup
- `Set` (set, frozenset) — membership and set algebra operators

## Closing Thoughts
Understanding the data model is the prerequisite for writing truly Pythonic code. Every part of the language — from `for` loops to `with` statements to `+` operators — is defined in terms of special methods. Build objects that speak this protocol and they immediately work everywhere Python works.

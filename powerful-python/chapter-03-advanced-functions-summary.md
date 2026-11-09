# Chapter 3 – Advanced Functions

## Core Idea
Functions in Python are **first-class objects** — they can be stored in variables, passed as arguments, and returned from other functions. This unlocks powerful abstractions. Combined with flexible argument syntax (`*args`, `**kwargs`), Python functions become remarkably expressive.

## Key Concepts

### Variable Positional Arguments (`*args`)
- Prefix with `*` to accept any number of positional arguments as a **tuple**:
```python
def read_files(*paths):
    for path in paths:
        ...
```
- Naming it `args` is a strong convention, but a descriptive name (like `paths`) improves readability

### Argument Unpacking
- Use `*` when **calling** a function to unpack a list/tuple into positional arguments:
```python
book_info = get_required_textbook(4242)
order_book(*book_info)  # unpacks (title, author, isbn)
```
- Key distinction: `*` in a **def** packs args into a tuple; `*` in a **call** unpacks a sequence

### Variable Keyword Arguments (`**kwargs`)
- Prefix with `**` to accept any number of keyword arguments as a **dict**:
```python
def print_kwargs(**kwargs):
    for key, value in kwargs.items():
        print(f"{key} -> {value}")
```

### Keyword Unpacking
- Use `**` when calling to unpack a dict into keyword arguments:
```python
numbers = {"a": 7, "b": 5, "c": 3}
normal_function(**numbers)
```
- Dictionary keys must exactly match the function's parameter names

### Combining Both
```python
def general_function(*args, **kwargs): ...

nums = (3, 4)
extras = {"d": 5, "e": 2}
addup(*nums, **extras)
```
Order in `def`: positional args → `*args` → `**kwargs`

### Functions as Objects
- Functions can be stored in variables, passed as arguments, or returned from other functions
- This enables **key functions** — a function that extracts a comparison value from an element:
```python
def max_by_key(items, key):
    biggest = items[0]
    for item in items[1:]:
        if key(item) > key(biggest):
            biggest = item
    return biggest

max_by_key(nums, int)       # pass the function, not int()
max_by_key(integers, abs)
max_by_key(students, get_gpa)
```

### Built-in Key Functions
Python's `max()`, `min()`, and `sorted()` all accept a `key=` argument:
```python
max(nums, key=int)
sorted(students, key=get_gpa)
```

### `operator` Module Helpers
| Helper | Use |
|---|---|
| `itemgetter("gpa")` | Key function for dict field or tuple index |
| `attrgetter("gpa")` | Key function for object attribute |
| `methodcaller("method")` | Key function for object method return value |

```python
from operator import itemgetter, attrgetter
sorted(students, key=itemgetter("gpa"))
sorted(student_objs, key=attrgetter("gpa"))
```

## Key Takeaways
- `*args` and `**kwargs` make functions maximally flexible; use them deliberately
- The `*` and `**` prefixes at call sites **unpack** collections into arguments
- Treating functions as objects unlocks **key function** patterns — pass the function itself, not its result
- `max()`, `min()`, `sorted()` all support `key=` — use it instead of writing custom sort logic
- `operator.itemgetter` / `attrgetter` create reusable key functions without writing a lambda or def

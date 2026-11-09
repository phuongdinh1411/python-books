# Chapter 2 – Creating Collections with Comprehensions

## Core Idea
**Comprehensions** are a high-level, declarative way to create collections in Python. They are more readable, more concise, and often more performant than equivalent `for` loops. Mastering them — including generator expressions — unlocks a major level of Pythonic expressiveness.

## Key Concepts

### List Comprehensions
Structure: `[ EXPRESSION for VARIABLE in SEQUENCE ]`
```python
squares = [n*n for n in range(6)]
```
- The `SEQUENCE` can be any iterable
- Add an `if` clause to filter: `[ EXPR for VAR in SEQ if CONDITION ]`
```python
[word for word in words if is_palindrome(word)]
```

### Formatting for Readability
Split comprehensions across lines — each clause on its own line:
```python
def double_short_words(words):
    return [
        word + word
        for word in words
        if len(word) < 5
    ]
```
Benefits: more readable, cleaner version-control diffs, easier code review

### Multiple `for` Clauses
- **Independent**: produces the Cartesian product of two sequences
- **Chained**: second `for` source depends on the first variable
```python
# Flatten a list of ranges
[float(num) for subrange in ranges for num in subrange]
```
Order matters: parse left to right — variables must be defined before being used

### Multiple `if` Clauses
- Multiple `if` clauses are **AND-ed** together
- For OR logic, combine into a single `if` with `or`

### Generator Expressions
- Swap `[...]` for `(...)` to get a **lazy generator object** instead of a list:
```python
generated_squares = (n*n for n in range(NUM_SQUARES))
```
- Same memory-efficiency benefits as generator functions
- Can omit inner parentheses when passing as the sole argument to a function:
```python
sorted(user.email for user in all_users if user.is_active)
```
- Use a list comprehension when you actually need random access, multiple passes, or appending — otherwise prefer a generator expression

### Dictionary and Set Comprehensions
```python
# Dict comprehension
{student.name: student.gpa for student in students}

# Set comprehension (automatically deduplicates)
{student.major for student in students}
```
- Dict expression field is `key: value`; set is a single value
- Curly braces distinguish both from list comprehensions

### "Tuple Comprehensions"
Python has no native tuple comprehension, but you can simulate one:
```python
tuple(student.gpa for student in students if student.major == "CS")
```
Same pattern works for `dict()` and `set()` constructors with generator expressions.

## Key Takeaways
- Use comprehensions to replace `append`-style `for` loops — they are more declarative and readable
- Split multi-clause comprehensions across lines for readability and clean diffs
- Prefer **generator expressions** over list comprehensions when you don't need a full list
- Dictionary, set, and "tuple" comprehensions follow the same mental model as list comprehensions

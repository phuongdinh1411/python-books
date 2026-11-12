# Chapter 13 – Managing Subprocesses

## Core Idea
Chapter 13 covers `asyncio.create_subprocess_exec` and `asyncio.create_subprocess_shell` — the async-native APIs for spawning and communicating with child processes without blocking the event loop. Common use cases include running shell commands, processing their output as a stream, and sending data to their stdin.

---

## Why Async Subprocesses?

`subprocess.run()` blocks the thread until the subprocess finishes. In an async application this freezes the event loop. asyncio's subprocess API wraps the process in a coroutine so the event loop can continue handling other tasks while waiting for output.

---

## `asyncio.create_subprocess_exec`

Preferred for running a known command with explicit arguments (no shell injection risk):

```python
import asyncio

async def run_command():
    process = await asyncio.create_subprocess_exec(
        'ls', '-la',
        stdout=asyncio.subprocess.PIPE,   # capture stdout
        stderr=asyncio.subprocess.PIPE,   # capture stderr
    )
    stdout, stderr = await process.communicate()   # wait for completion
    print(stdout.decode())
    print(f'Return code: {process.returncode}')

asyncio.run(run_command())
```

### `create_subprocess_exec` vs `create_subprocess_shell`

| | `create_subprocess_exec` | `create_subprocess_shell` |
|---|---|---|
| Arguments | List of strings (no shell) | Single shell command string |
| Shell injection risk | ❌ None | ⚠️ Possible |
| Best for | Known programs with explicit args | Simple one-liners, pipes |

```python
# Shell variant (use cautiously)
process = await asyncio.create_subprocess_shell(
    'ls -la | grep ".py"',
    stdout=asyncio.subprocess.PIPE
)
```

---

## Process Communication

### `communicate()` — Simple, Buffered
Reads all stdout/stderr at once. Good when output is small.

```python
stdout, stderr = await process.communicate(input=b'some input\n')
```

### Streaming Output Line by Line
For large output, stream it to avoid buffering the whole result in memory:

```python
async def stream_output():
    process = await asyncio.create_subprocess_exec(
        'python3', 'long_running_script.py',
        stdout=asyncio.subprocess.PIPE
    )

    while True:
        line = await process.stdout.readline()
        if not line:
            break
        print(f'Output: {line.decode().rstrip()}')

    await process.wait()
    print(f'Finished with code {process.returncode}')
```

---

## Running Multiple Subprocesses Concurrently

```python
import asyncio

async def run_script(name: str, delay: int) -> str:
    process = await asyncio.create_subprocess_exec(
        'python3', '-c', f'import time; time.sleep({delay}); print("{name} done")',
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    return stdout.decode().strip()

async def main():
    # Run three subprocesses concurrently
    results = await asyncio.gather(
        run_script('A', 1),
        run_script('B', 2),
        run_script('C', 1),
    )
    for r in results:
        print(r)
    # Total time ≈ 2s, not 4s

asyncio.run(main())
```

---

## Writing to stdin

```python
async def interactive_process():
    process = await asyncio.create_subprocess_exec(
        'python3', '-c', 'print(input())',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate(input=b'Hello from parent\n')
    print(stdout.decode())   # 'Hello from parent'
```

---

## Terminating Subprocesses

```python
process = await asyncio.create_subprocess_exec('long_running_program')

await asyncio.sleep(5)
process.terminate()            # SIGTERM — graceful
await asyncio.sleep(1)
if process.returncode is None:
    process.kill()             # SIGKILL — forceful
await process.wait()
```

---

## Timeouts with Subprocesses

Use `asyncio.wait_for` to add a timeout:

```python
try:
    stdout, _ = await asyncio.wait_for(
        process.communicate(),
        timeout=10.0
    )
except asyncio.TimeoutError:
    process.kill()
    await process.wait()
    raise
```

---

## Key Takeaway
Use `asyncio.create_subprocess_exec` to run subprocesses without blocking the event loop. `communicate()` is convenient for short output; stream `readline()` for large or continuous output. `asyncio.gather` runs multiple subprocesses concurrently. Always handle process termination explicitly and pair with `asyncio.wait_for` for timeout protection.

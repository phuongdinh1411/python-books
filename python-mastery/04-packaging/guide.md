# Pillar 4 — Packaging

> **Duration:** 1 week | **Priority:** 🟡 Medium

---

## 🎯 Learning Objectives

- Understand the modern Python packaging ecosystem (`pyproject.toml`, PEP 517/518/621)
- Set up a project correctly from scratch with virtual environments
- Manage dependencies (pinning, optional extras, dev deps)
- Build distributable packages (sdist + wheel) and publish to PyPI
- Use `uv` as a fast, modern replacement for pip + venv

---

## 📚 Resources

| Resource | Type | Priority |
|----------|------|----------|
| [packaging.python.org](https://packaging.python.org) | 📄 Docs | Must |
| [Hypermodern Python series](https://cjolowicz.github.io/posts/hypermodern-python-01-setup/) | 📄 Blog | Must |
| [uv docs](https://docs.astral.sh/uv/) | 📄 Docs | Must |
| [hatch docs](https://hatch.pypa.io/) | 📄 Docs | Recommended |

---

## Section 1 — The Modern Packaging Ecosystem

### Key Files

```
my_project/
├── pyproject.toml        ← THE central config file (replaces setup.py, setup.cfg)
├── README.md
├── LICENSE
├── CHANGELOG.md
├── src/
│   └── my_project/
│       ├── __init__.py
│       └── ...
└── tests/
    └── ...
```

### Why `src/` Layout?

```
Without src/:
  my_project/
  ├── my_project/    ← importable from project root
  └── tests/
  Problem: `import my_project` works without installation!
           Tests can pass locally but fail in CI/prod.

With src/:
  my_project/
  ├── src/
  │   └── my_project/   ← only importable after `pip install -e .`
  └── tests/
  Benefit: Forces proper installation; tests always test the installed package.
```

---

## Section 2 — `pyproject.toml` Deep Dive

### Minimal Example

```toml
# pyproject.toml

[build-system]
requires = ["hatchling"]           # the build backend
build-backend = "hatchling.build"  # PEP 517 build backend

[project]
name = "my-awesome-lib"
version = "0.1.0"
description = "A short description"
readme = "README.md"
license = { file = "LICENSE" }
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["python", "library"]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
requires-python = ">=3.11"

dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "mypy",
    "ruff",
]
postgres = [
    "asyncpg>=0.29",
    "sqlalchemy[asyncio]>=2.0",
]

[project.urls]
Homepage = "https://github.com/you/my-awesome-lib"
Documentation = "https://my-awesome-lib.readthedocs.io"

[project.scripts]
my-cli = "my_project.cli:main"   # creates a CLI entry point
```

### Version Specifiers

```toml
dependencies = [
    "requests",              # any version (bad practice)
    "requests>=2.28",        # minimum version
    "requests>=2.28,<3.0",   # compatible range
    "requests~=2.28",        # ~= means >=2.28, <3.0 (tilde operator)
    "requests==2.28.2",      # exact pin (for apps, not libraries)
]
```

**Rule:**
- **Libraries:** use `>=` lower bound only (let users choose)
- **Applications:** pin exact versions (`==`) in a lockfile

---

## Section 3 — `uv` — The Modern Package Manager

`uv` is a fast Python package manager written in Rust that replaces:
- `pip` (install packages)
- `venv` (virtual environments)
- `pip-tools` (lockfiles)
- `pipx` (install CLI tools)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new project
uv init my-project
cd my-project

# Create and activate venv
uv venv                    # creates .venv/
source .venv/bin/activate  # activate (Unix)
.venv\Scripts\activate     # activate (Windows)

# Install dependencies
uv add httpx pydantic        # adds to [project.dependencies]
uv add --dev pytest ruff     # adds to [project.optional-dependencies].dev
uv add --group postgres asyncpg sqlalchemy  # named extras

# Install all deps (from pyproject.toml)
uv sync                      # installs + creates uv.lock

# Install with optional extras
uv sync --extra dev --extra postgres

# Remove a package
uv remove httpx

# Run a command in the venv
uv run pytest
uv run python -m my_project

# Upgrade packages
uv lock --upgrade             # regenerate lockfile with latest versions
uv sync                       # apply the new lockfile
```

### `uv.lock` — The Lockfile

```bash
# After `uv sync`, a uv.lock is created:
# - Exact versions of all dependencies (direct + transitive)
# - Commit this to Git for reproducible builds!
# - Never edit manually

git add uv.lock   # commit the lockfile
```

---

## Section 4 — Building and Publishing

### Build a Distribution

```bash
# Install build tools
pip install build twine

# Build both sdist (.tar.gz) and wheel (.whl)
python -m build

# Output:
# dist/
# ├── my_awesome_lib-0.1.0.tar.gz      ← source distribution
# └── my_awesome_lib-0.1.0-py3-none-any.whl  ← wheel (preferred)

# Or with uv
uv build
```

### What is a Wheel?

```
.whl file is a zip archive containing:
  - Your compiled package
  - Metadata (name, version, deps)
  - No build step needed on install!

sdist (.tar.gz):
  - Source code
  - Build step required on install
  - Needed for packages with C extensions
```

### Publish to TestPyPI (safe practice)

```bash
# Create account at test.pypi.org
# Get your API token

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Or with uv:
uv publish --index-url https://test.pypi.org/legacy/

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ my-awesome-lib
```

### Publish to Real PyPI

```bash
twine upload dist/*
# Enter your API token when prompted
```

---

## Section 5 — Virtual Environments

### Manual `venv`

```bash
# Create
python -m venv .venv

# Activate (Unix/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Deactivate
deactivate

# Delete and recreate
rm -rf .venv && python -m venv .venv
```

### Why Virtual Environments?

```
Without venv:
  pip install requests → goes into system Python
  Project A needs requests==2.27
  Project B needs requests==2.31
  CONFLICT — only one can be installed globally!

With venv:
  Project A: .venv/ with requests==2.27
  Project B: .venv/ with requests==2.31
  Both work independently.
```

---

## Section 6 — `hatch` — All-in-One Tool

`hatch` is an alternative to `uv` with more features for managing multiple environments.

```bash
pip install hatch

# Create project
hatch new my-project
cd my-project

# Create and use environments
hatch env create
hatch run python   # runs in default env

# Run tests
hatch run test:pytest

# Multiple environments in pyproject.toml
```

```toml
# hatch environments
[tool.hatch.envs.default]
dependencies = ["pytest", "coverage"]

[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
cov = "coverage run -m pytest {args:tests}"

[tool.hatch.envs.lint]
dependencies = ["ruff", "mypy"]

[tool.hatch.envs.lint.scripts]
check = ["ruff check .", "mypy src/"]
```

---

## Section 7 — Project Versioning

### Dynamic Version from Git Tags

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"   # reads from git tags (requires hatch-vcs)
```

```bash
# Tag a release
git tag v1.2.0
git push --tags
# hatch builds with version=1.2.0 automatically
```

### `importlib.metadata` — Read Version at Runtime

```python
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("my-awesome-lib")
except PackageNotFoundError:
    __version__ = "unknown"
```

---

## Section 8 — Code Quality Tools (goes in `pyproject.toml`)

```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "UP", "B"]   # error, pyflakes, isort, upgrades, bugbear
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--cov=src --cov-report=html"

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
```

---

## 🏋️ Exercises

### Exercise 1 — Create and Publish a Package
1. Create a package `str-tools` with 3 utility functions
2. Set up `pyproject.toml` with metadata, deps, and optional `dev` extras
3. Write tests with pytest
4. Build and publish to TestPyPI
5. Install it in a fresh venv and verify it works

### Exercise 2 — Migrate a Project to `src/` Layout
Take an existing script and restructure it into:
```
src/my_tool/__init__.py
src/my_tool/cli.py
tests/test_cli.py
pyproject.toml
```

### Exercise 3 — Lockfile Management
Using `uv`:
1. Create a project with 5 dependencies
2. Generate a lockfile (`uv.lock`)
3. Simulate a dependency upgrade
4. Verify nothing breaks after `uv sync`

---

## ✅ Self-Check Questions

1. What does `pyproject.toml` replace?
2. What is the difference between `sdist` and `wheel`?
3. Why is the `src/` layout recommended?
4. What is a lockfile and when should you commit it?
5. What does `~=2.28` mean as a version specifier?
6. How does `uv add --dev` differ from `uv add`?
7. What is an entry point (`[project.scripts]`)?
8. What is `importlib.metadata` used for?

---

## 🔗 Key Links

- https://packaging.python.org/en/latest/tutorials/packaging-projects/
- https://docs.astral.sh/uv/
- https://hatch.pypa.io/
- https://cjolowicz.github.io/posts/hypermodern-python-01-setup/
- https://test.pypi.org/

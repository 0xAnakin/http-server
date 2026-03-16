# http-server

An asynchronous HTTP server built from scratch in Python 3.12 — a learning
project for developers coming from JavaScript / C++.

---

## How this project was set up

Below is every step that was used to scaffold this workspace, explained so you
can reproduce it or understand what each piece does.

### 1. Initialize the project with `uv`

```bash
uv init --python 3.12
```

**What happened:**

| File created      | Purpose                                                        | JS / C++ analogy       |
|-------------------|----------------------------------------------------------------|------------------------|
| `pyproject.toml`  | Project metadata & tool configuration (the single config file) | `package.json`         |
| `.python-version` | Pins the Python version to 3.12                                | `.nvmrc` / `.node-version` |
| `main.py`         | Default entry point (we removed it — see step 3)               | `index.js`             |
| `.gitignore`      | Ignores `__pycache__/`, `.venv/`, build artifacts              | same as JS             |
| `README.md`       | This file                                                      | same                   |

`uv` also created a **virtual environment** at `.venv/`. A virtual environment
is an isolated Python installation for this project — similar to `node_modules`
being local to each JS project. It prevents packages from one project
conflicting with another.

### 2. Add dev dependencies

```bash
uv add --dev mypy pytest ruff
```

This installed three development tools (they won't ship with the final product):

| Package  | What it does                             | JS equivalent         |
|----------|------------------------------------------|------------------------|
| **ruff** | Linter + code formatter (incredibly fast, written in Rust) | ESLint + Prettier |
| **mypy** | Static type checker (reads type hints)   | TypeScript (`tsc`)     |
| **pytest** | Test runner & assertion library         | Jest / Mocha           |

`uv add --dev` wrote them into the `[dependency-groups] dev` section of
`pyproject.toml` and created/updated `uv.lock` (the lockfile — like
`package-lock.json`).

### 3. Create the `src` layout

We deleted the default `main.py` and created a proper package:

```
src/
  http_server/          ← the importable package (note: underscore, not hyphen)
    __init__.py         ← makes this directory a package (like index.js)
    __main__.py         ← runs when you do `python -m http_server`
    server.py           ← the actual server code
tests/
  __init__.py
  test_server.py        ← first test
```

**Why `src/` layout?** It forces Python to import the *installed* package
rather than the raw source directory. This catches packaging bugs early. It's
a widely-recommended best practice (see
[Hynek's article](https://hynek.me/articles/testing-packaging/)).

**Why underscores?** Python package names must be valid identifiers.
`http-server` has a hyphen, which isn't allowed in `import` statements, so the
package directory is `http_server` (underscored). The project name in
`pyproject.toml` can keep the hyphen — pip/uv handle the mapping.

### 4. Configure tools in `pyproject.toml`

All three tools read their config from `pyproject.toml` (one file to rule them
all — unlike JS where you often have `.eslintrc`, `.prettierrc`, `tsconfig.json`,
`jest.config.js`, etc.).

See the `[tool.ruff]`, `[tool.mypy]`, and `[tool.pytest.ini_options]` sections
in `pyproject.toml` — every setting is commented.

### 5. Build system

We added a `[build-system]` section using **hatchling** so Python knows how to
install the package from the `src/` directory. This is analogous to the `"main"`
and `"exports"` fields in `package.json`.

---

## Quick-start commands

```bash
# Run the server
uv run python -m http_server

# Run tests
uv run pytest

# Type-check the source code
uv run mypy src/

# Lint (find problems)
uv run ruff check .

# Auto-format code
uv run ruff format .
```

> **Why `uv run` everywhere?**
> `uv run` makes sure the command executes inside the project's virtual
> environment — like `npx` ensures you use the local binary. You *could*
> activate the venv manually (`source .venv/bin/activate` / `.venv\Scripts\Activate.ps1`)
> and then drop the `uv run` prefix, but `uv run` is simpler and more reliable.

---

## Project file reference

| File / Dir           | Purpose |
|----------------------|---------|
| `pyproject.toml`     | All project metadata + tool config (the Python `package.json`) |
| `uv.lock`            | Locked dependency versions (like `package-lock.json`) |
| `.python-version`    | Pins Python to 3.12 |
| `src/http_server/`   | The main package source code |
| `tests/`             | Test suite (pytest) |
| `AGENTS.md`          | Instructions for Copilot on how to assist with this project |
| `.venv/`             | Virtual environment (auto-created, **do not commit**) |

---

## What's next

We'll start building the actual HTTP server step by step:

1. **TCP listener** — accept raw socket connections with `asyncio`
2. **HTTP parsing** — parse request lines, headers, and bodies
3. **Router** — map URL paths to handler functions
4. **Response builder** — construct proper HTTP responses
5. **Static file serving** — serve files from disk
6. **Middleware** — logging, error handling, etc.

Each step will be heavily commented with JS/C++ comparisons.

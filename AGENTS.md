# AGENTS.md — Copilot Agent Instructions

## Project Context

This is a **Python learning project** for a senior JavaScript developer.
The goal is to build an asynchronous HTTP server from scratch using Python 3.12.

## Code Style & Conventions

- **Comment everything extensively.** The developer is learning Python, so every
  new concept, idiom, or standard-library feature must be explained in comments
  — especially with comparisons to JavaScript equivalents.
- Use **type hints** on all function signatures and module-level variables
  (the project runs mypy in strict mode).
- Follow **PEP 8** naming conventions:
  - `snake_case` for functions, variables, and module names (not camelCase)
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Keep lines under **99 characters** (configured in ruff).
- Use **double quotes** for strings (configured in ruff formatter).
- Use **4-space indentation** (Python standard).

## Project Structure

```
http-server/
├── src/http_server/     # Main package (src layout)
│   ├── __init__.py      # Package init — exports public API
│   ├── __main__.py      # `python -m http_server` entry point
│   └── server.py        # The async HTTP server logic
├── tests/               # Pytest test suite
│   ├── __init__.py
│   └── test_server.py
├── pyproject.toml       # Project config (like package.json)
├── README.md
└── AGENTS.md            # This file
```

## Tooling

| Tool   | Purpose              | JS Equivalent          |
|--------|----------------------|------------------------|
| uv     | Package manager      | npm / pnpm             |
| ruff   | Linter + formatter   | ESLint + Prettier      |
| mypy   | Static type checker  | TypeScript compiler    |
| pytest | Test runner          | Jest / Mocha           |

### Running tools

```bash
uv run python -m http_server   # Run the server
uv run pytest                  # Run tests
uv run mypy src/               # Type-check
uv run ruff check .            # Lint
uv run ruff format .           # Auto-format
```

## Teaching Approach

- Introduce **one concept at a time** — don't overload with too many new ideas.
- When writing new code, add comments comparing Python to JS where helpful.
- Keep functions small and focused so each one can be studied independently.
- Prefer the **standard library** (`asyncio`, `socket`) over third-party
  packages to maximize learning.

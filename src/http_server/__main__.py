# ──────────────────────────────────────────────────────────────
# __main__.py  —  Package entry point
# ──────────────────────────────────────────────────────────────
#
# This file is executed when you run the package as a script:
#     python -m http_server          (or:  uv run python -m http_server)
#
# It's analogous to the "main" field in package.json, or the `int main()`
# function in C++.  Python looks for __main__.py inside the package
# whenever you use the `-m` (module) flag.
#
# IMPORTANT PYTHON CONCEPT — `if __name__ == "__main__":` guard
#   Every Python file has a built-in variable called __name__.
#   • When the file is *run directly*, __name__ is set to "__main__".
#   • When the file is *imported* by another file, __name__ is set to the
#     module's dotted path (e.g. "http_server.__main__").
#
#   The guard prevents the code inside from running on import — just like
#   how in C++ you wouldn't want `main()` to run when you #include a header.
#
# We keep this file thin — it only calls into the real logic.  This makes
# the code easier to test (you can import `main` without side-effects).
# ──────────────────────────────────────────────────────────────

from http_server.server import main  # import the main function from server.py

if __name__ == "__main__":
    main()

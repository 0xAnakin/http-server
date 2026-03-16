# ──────────────────────────────────────────────────────────────
# __init__.py  —  Package initializer
# ──────────────────────────────────────────────────────────────
#
# In Python, a directory becomes an "importable package" when it contains an
# __init__.py file.  This is similar to having an index.ts / index.js that
# re-exports symbols from a folder, or a header file in C++ that declares
# the public API of a module.
#
# When someone writes:
#     from http_server import __version__
# Python executes THIS file first, then hands back whatever name was requested.
#
# You can leave __init__.py completely empty and it still works — its mere
# existence is what matters.  But it's a nice place to expose a public API
# so users don't need to know your internal file layout.
#
# Key Python concept — "dunder" names:
#   Names wrapped in double underscores like __version__ are called "dunder"
#   (double-under) names.  They're a Python convention for special/magic
#   attributes.  __version__ is not enforced by the language; it's just a
#   widely-followed convention (like package.json's "version" field).
# ──────────────────────────────────────────────────────────────

__version__ = "0.1.0"

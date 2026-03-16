# ──────────────────────────────────────────────────────────────
# request.py  —  HTTP request parser
# ──────────────────────────────────────────────────────────────
#
# This module parses raw HTTP request bytes into a structured object.
# Instead of working with a giant string, we'll have an object with
# `.method`, `.path`, `.headers`, etc.
#
# KEY NEW CONCEPT — dataclasses
#
#   A dataclass is Python's concise way to create a class that mainly
#   holds data — like a TypeScript interface or a plain JS object, but
#   with type annotations and auto-generated methods.
#
#   JS:
#     // You'd either use a plain object:
#     const request = { method: "GET", path: "/", headers: {} };
#     // Or a TypeScript interface:
#     interface HttpRequest { method: string; path: string; headers: Record<string, string>; }
#
#   Python (without dataclass — verbose):
#     class HttpRequest:
#         def __init__(self, method: str, path: str, headers: dict):
#             self.method = method
#             self.path = path
#             self.headers = headers
#
#   Python (with dataclass — clean):
#     @dataclass
#     class HttpRequest:
#         method: str
#         path: str
#         headers: dict[str, str]
#
#   The `@dataclass` decorator auto-generates __init__, __repr__ (toString),
#   __eq__ (equality comparison), and more. It's like a struct with batteries.
#
# KEY NEW CONCEPT — decorators (@something)
#
#   A decorator is a function that wraps another function or class.
#   The `@` syntax is just shorthand:
#
#     @dataclass
#     class Foo: ...
#
#   is the same as:
#
#     class Foo: ...
#     Foo = dataclass(Foo)
#
#   JS doesn't have built-in decorators (there's a TC39 proposal), but
#   you've likely seen them in TypeScript/Angular/NestJS:
#     @Injectable()
#     class MyService { ... }
#
# KEY NEW CONCEPT — dict (dictionary)
#
#   Python's `dict` is like JS's plain object or `Map`:
#     JS:      const headers = { "Content-Type": "text/html" };
#     Python:  headers = {"Content-Type": "text/html"}
#
#   Access is similar:
#     JS:      headers["Content-Type"]     // or headers.contentType
#     Python:  headers["Content-Type"]     // dot access doesn't work for dicts
#
#   The type hint `dict[str, str]` means "a dict with string keys and
#   string values" — like `Record<string, string>` in TypeScript.
# ──────────────────────────────────────────────────────────────

from dataclasses import dataclass, field  # built-in module for data-holding classes


@dataclass
class HttpRequest:
    """
    A parsed HTTP request.

    This is a simple data container — just holds the parts of the request
    after we break apart the raw bytes.  Think of it like a TypeScript interface:

        interface HttpRequest {
            method: string;      // "GET", "POST", etc.
            path: string;        // "/", "/about", "/api/users"
            version: string;     // "HTTP/1.1"
            headers: Record<string, string>;
            body: string;
        }
    """

    method: str  # "GET", "POST", "PUT", "DELETE", etc.
    path: str  # The URL path, e.g. "/" or "/about"
    version: str  # The HTTP version, e.g. "HTTP/1.1"

    # `field(default_factory=dict)` means "default to an empty dict".
    # We can't write `headers: dict = {}` because mutable defaults are
    # shared between ALL instances (a famous Python gotcha — like a JS
    # closure over a shared reference). `default_factory` creates a NEW
    # empty dict for each instance.
    #
    # JS equivalent of the bug:
    #   function create(headers = []) { headers.push("x"); return headers; }
    #   create();  // ["x"]
    #   create();  // ["x"] — wait, it should be empty!
    #   // That doesn't actually happen in JS (defaults are re-evaluated),
    #   // but in Python, default values are evaluated ONCE at class definition.
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""


def parse_request(raw: bytes) -> HttpRequest:
    """
    Parse raw HTTP request bytes into an HttpRequest object.

    An HTTP request looks like this (each line ends with \\r\\n):

        GET /about HTTP/1.1\\r\\n          ← request line
        Host: localhost:8000\\r\\n          ← header
        User-Agent: curl/8.0\\r\\n          ← header
        Accept: */*\\r\\n                   ← header
        \\r\\n                              ← blank line (end of headers)
        optional body here                 ← body (for POST/PUT requests)

    Parameters
    ----------
    raw : bytes
        The raw bytes received from the TCP socket.

    Returns
    -------
    HttpRequest
        A structured object with method, path, version, headers, and body.
    """
    # ── 1. Decode bytes → string ─────────────────────────────
    # Same as Buffer.from(raw).toString("utf-8") in Node.
    text = raw.decode("utf-8")

    # ── 2. Split headers from body ───────────────────────────
    # HTTP uses a blank line (\r\n\r\n) to separate headers from body.
    # `str.split(separator, maxsplit)` — the second argument limits how
    # many splits happen. We only want to split ONCE (there might be
    # \r\n\r\n sequences inside the body too).
    #
    # JS equivalent:
    #   const [headerSection, ...rest] = text.split("\r\n\r\n");
    #   const body = rest.join("\r\n\r\n");
    #
    # Python's `split(sep, 1)` returns a list of at most 2 elements.
    parts = text.split("\r\n\r\n", 1)
    header_section = parts[0]
    # If there's a body after the blank line, grab it; otherwise empty string.
    body = parts[1] if len(parts) > 1 else ""

    # ── 3. Split the header section into lines ───────────────
    # `str.splitlines()` is another option, but we use split("\r\n")
    # because HTTP specifically uses \r\n line endings (not just \n).
    lines = header_section.split("\r\n")

    # ── 4. Parse the request line (first line) ───────────────
    # The request line has exactly three parts:  "GET / HTTP/1.1"
    # `str.split()` with no arguments splits on any whitespace.
    #
    # JS equivalent:
    #   const [method, path, version] = lines[0].split(" ");
    #
    # Python's unpacking works the same way as JS destructuring:
    #   JS:     const [a, b, c] = [1, 2, 3];
    #   Python: a, b, c = [1, 2, 3]
    request_line = lines[0]
    method, path, version = request_line.split(" ", 2)

    # ── 5. Parse headers into a dict ─────────────────────────
    # Each header is "Key: Value". We split on ": " (note the space)
    # and build a dictionary.
    #
    # JS equivalent:
    #   const headers = {};
    #   for (const line of lines.slice(1)) {
    #       const [key, ...rest] = line.split(": ");
    #       headers[key.toLowerCase()] = rest.join(": ");
    #   }
    #
    # We lowercase the keys because HTTP headers are case-insensitive
    # (RFC 7230 §3.2). "Content-Type" and "content-type" are the same.
    headers: dict[str, str] = {}
    for line in lines[1:]:  # lines[1:] is slice notation — skips the first line
        if ": " in line:
            # `split(": ", 1)` splits on the FIRST ": " only.
            # This handles headers whose values contain ": " (e.g. timestamps).
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    # ── 6. Build and return the HttpRequest ──────────────────
    # Just like:  return { method, path, version, headers, body };  in JS
    return HttpRequest(
        method=method,
        path=path,
        version=version,
        headers=headers,
        body=body,
    )

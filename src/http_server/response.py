# ──────────────────────────────────────────────────────────────
# response.py  —  HTTP response builder
# ──────────────────────────────────────────────────────────────
#
# This module provides a structured way to build HTTP responses.
# Instead of assembling raw strings by hand, we use an HttpResponse
# object with a clean API, then serialize it to bytes at the end.
#
# KEY NEW CONCEPT — methods on a dataclass
#
#   So far our dataclasses (HttpRequest) were pure data containers.
#   But dataclasses can have methods too — they're still regular classes.
#
#   JS equivalent:
#     class HttpResponse {
#         constructor(status, headers, body) { ... }
#         toBytes() { return Buffer.from(this.serialize()); }
#     }
#
#   Python dataclass with a method:
#     @dataclass
#     class HttpResponse:
#         status: int
#         def to_bytes(self) -> bytes: ...
#
#   The `@dataclass` decorator adds __init__ etc., but you can still
#   define custom methods alongside the auto-generated ones.
#
# KEY NEW CONCEPT — `self` parameter
#
#   In JS, `this` is implicit inside methods:
#     class Foo { greet() { return this.name; } }
#
#   In Python, the instance reference is an EXPLICIT first parameter
#   called `self` (it's a convention, not a keyword — but always use `self`):
#     class Foo:
#         def greet(self) -> str:
#             return self.name
#
#   `self` IS `this`. Python just makes you spell it out.
#
# KEY NEW CONCEPT — Enum (enumeration)
#
#   An Enum is a set of named constants — like TypeScript's `enum`:
#
#   TypeScript:
#     enum HttpStatus { OK = 200, NOT_FOUND = 404 }
#
#   Python:
#     class HttpStatus(IntEnum):
#         OK = 200
#         NOT_FOUND = 404
#
#   We use IntEnum (a subclass of int + Enum) so values can be used
#   directly as numbers (e.g. in f-strings, comparisons).
# ──────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from enum import IntEnum  # built-in module for creating enumerations


class HttpStatus(IntEnum):
    """
    Common HTTP status codes as an enum.

    Using an enum instead of bare numbers (200, 404) gives us:
    - Autocomplete in the editor
    - A human-readable name attached to each code
    - Type safety (mypy can catch wrong values)

    JS equivalent:
        const HttpStatus = { OK: 200, NOT_FOUND: 404, ... } as const;
        // or: enum HttpStatus { OK = 200, NOT_FOUND = 404 }  (TypeScript)
    """

    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500


# A mapping from status code → reason phrase (the text after the number).
# HTTP/1.1 requires a reason phrase in the status line: "HTTP/1.1 200 OK".
#
# `dict[int, str]` = a dict with int keys and str values.
# JS equivalent: `const REASON_PHRASES: Record<number, string> = { 200: "OK", ... }`
REASON_PHRASES: dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}


@dataclass
class HttpResponse:
    """
    A builder for HTTP responses.

    Usage (similar to how you'd build a response in Express):

        JS (Express):
            res.status(200)
               .set("Content-Type", "text/plain")
               .send("Hello!");

        Python (ours):
            response = HttpResponse(status=HttpStatus.OK, body="Hello!")
            raw_bytes = response.to_bytes()
    """

    # The HTTP status code (200, 404, etc.)
    status: int = HttpStatus.OK

    # Response headers — same structure as request headers.
    # `field(default_factory=dict)` creates a fresh empty dict per instance
    # (remember: mutable defaults are shared in Python — this avoids the bug).
    headers: dict[str, str] = field(default_factory=dict)

    # The response body as a string. Empty by default.
    body: str = ""

    # The HTTP version to use in the status line.
    version: str = "HTTP/1.1"

    def to_bytes(self) -> bytes:
        """
        Serialize this response into raw HTTP bytes ready to send over TCP.

        Builds the full HTTP response string:
            HTTP/1.1 200 OK\\r\\n
            Content-Type: text/plain\\r\\n
            Content-Length: 13\\r\\n
            Connection: close\\r\\n
            \\r\\n
            Hello, World!

        Then encodes it to bytes (because TCP sockets speak bytes).

        Returns
        -------
        bytes
            The complete HTTP response as raw bytes.
        """
        # ── 1. Build the status line ─────────────────────────
        # Look up the reason phrase for this status code.
        # `dict.get(key, default)` returns the default if the key isn't found.
        # JS equivalent: `REASON_PHRASES[this.status] ?? "Unknown"`
        reason = REASON_PHRASES.get(self.status, "Unknown")
        status_line = f"{self.version} {self.status} {reason}"

        # ── 2. Auto-set Content-Length if there's a body ─────
        # Content-Length tells the client how many bytes the body is.
        # We set it automatically so the caller doesn't have to.
        #
        # IMPORTANT: we use `len(body.encode())` not `len(body)` because
        # Content-Length counts BYTES, not characters. For ASCII they're
        # the same, but for Unicode (e.g. emoji) they differ.
        # JS equivalent: `Buffer.byteLength(body, 'utf-8')`
        if self.body and "content-length" not in {k.lower() for k in self.headers}:
            self.headers["Content-Length"] = str(len(self.body.encode("utf-8")))

        # ── 3. Auto-set Connection: close ────────────────────
        # We close after each response for now (no keep-alive yet).
        if "connection" not in {k.lower() for k in self.headers}:
            self.headers["Connection"] = "close"

        # ── 4. Build the headers section ─────────────────────
        # Join all headers into "Key: Value\r\n" lines.
        #
        # This uses a generator expression inside `str.join()`:
        #   JS equivalent:
        #     Object.entries(headers).map(([k,v]) => `${k}: ${v}`).join("\r\n")
        #
        #   Python:
        #     "\r\n".join(f"{k}: {v}" for k, v in self.headers.items())
        #
        # Generator expressions are like array.map() but lazy — they don't
        # create a list in memory. They produce values one at a time.
        header_lines = "\r\n".join(f"{k}: {v}" for k, v in self.headers.items())

        # ── 5. Assemble the full response ────────────────────
        # Status line + headers + blank line + body
        raw = f"{status_line}\r\n{header_lines}\r\n\r\n{self.body}"

        # ── 6. Encode to bytes and return ────────────────────
        return raw.encode("utf-8")

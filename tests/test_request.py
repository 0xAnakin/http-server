# ──────────────────────────────────────────────────────────────
# test_request.py  —  Tests for the HTTP request parser
# ──────────────────────────────────────────────────────────────
#
# These are "unit tests" — they test the parse_request function in
# isolation, without starting a server or making network connections.
#
# This is like testing a pure utility function in Jest:
#   test("parses GET request", () => {
#       const result = parseRequest(rawBytes);
#       expect(result.method).toBe("GET");
#   });
#
# KEY NEW CONCEPT — test organization
#
#   In pytest, you can group related tests in a class (optional).
#   This is like Jest's `describe()` block — purely organizational:
#
#   JS (Jest):
#     describe("parse_request", () => {
#         it("should parse the method", () => { ... });
#     });
#
#   Python (pytest):
#     class TestParseRequest:
#         def test_parses_method(self) -> None: ...
#
#   The class name must start with `Test`. The `self` parameter is like
#   `this` in JS — but in Python you MUST list it explicitly (it's never
#   implicit). For simple test classes we don't use `self` at all, but
#   Python still requires it as the first parameter.
# ──────────────────────────────────────────────────────────────

from http_server.request import HttpRequest, parse_request


class TestParseRequest:
    """Tests for the parse_request() function."""

    def test_parses_get_request_line(self) -> None:
        """Parse method, path, and version from a simple GET request."""
        raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)

        assert result.method == "GET"
        assert result.path == "/"
        assert result.version == "HTTP/1.1"

    def test_parses_headers(self) -> None:
        """Headers should be parsed into a dict with lowercased keys."""
        raw = (
            b"GET /about HTTP/1.1\r\n"
            b"Host: localhost:8000\r\n"
            b"User-Agent: TestBrowser/1.0\r\n"
            b"Accept: text/html\r\n"
            b"\r\n"
        )
        result = parse_request(raw)

        # Keys are lowercased because HTTP headers are case-insensitive.
        assert result.headers["host"] == "localhost:8000"
        assert result.headers["user-agent"] == "TestBrowser/1.0"
        assert result.headers["accept"] == "text/html"

    def test_parses_path(self) -> None:
        """Different paths should be extracted correctly."""
        raw = b"GET /api/users HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)

        assert result.path == "/api/users"

    def test_parses_post_with_body(self) -> None:
        """POST requests can have a body after the blank line."""
        raw = (
            b"POST /submit HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n"
            b"Content-Length: 11\r\n"
            b"\r\n"
            b"name=Python"
        )
        result = parse_request(raw)

        assert result.method == "POST"
        assert result.path == "/submit"
        assert result.body == "name=Python"
        assert result.headers["content-type"] == "application/x-www-form-urlencoded"

    def test_empty_body_when_no_body(self) -> None:
        """GET requests typically have no body — body should be empty string."""
        raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)

        assert result.body == ""

    def test_returns_http_request_instance(self) -> None:
        """The result should be an HttpRequest dataclass instance."""
        raw = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = parse_request(raw)

        # `isinstance()` checks if an object is an instance of a class.
        # JS equivalent: `result instanceof HttpRequest`
        assert isinstance(result, HttpRequest)

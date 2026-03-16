# ──────────────────────────────────────────────────────────────
# test_response.py  —  Tests for the HTTP response builder
# ──────────────────────────────────────────────────────────────
#
# These unit tests verify that HttpResponse correctly serializes
# into valid HTTP response bytes.
#
# Note how each test focuses on ONE behavior — this makes it easy
# to pinpoint what broke if a test fails.  Same philosophy as in Jest.
# ──────────────────────────────────────────────────────────────

from http_server.response import HttpResponse, HttpStatus


class TestHttpResponse:
    """Tests for the HttpResponse dataclass and its to_bytes() method."""

    def test_simple_200_response(self) -> None:
        """A basic 200 OK response with a text body."""
        response = HttpResponse(
            status=HttpStatus.OK,
            headers={"Content-Type": "text/plain"},
            body="Hello!",
        )
        raw = response.to_bytes().decode()

        assert "HTTP/1.1 200 OK\r\n" in raw
        assert "Content-Type: text/plain\r\n" in raw
        assert "Hello!" in raw

    def test_auto_sets_content_length(self) -> None:
        """Content-Length should be set automatically based on the body."""
        response = HttpResponse(body="Hi")
        raw = response.to_bytes().decode()

        # "Hi" is 2 bytes in UTF-8.
        assert "Content-Length: 2\r\n" in raw

    def test_auto_sets_connection_close(self) -> None:
        """Connection: close should be added automatically."""
        response = HttpResponse(body="test")
        raw = response.to_bytes().decode()

        assert "Connection: close\r\n" in raw

    def test_does_not_override_existing_content_length(self) -> None:
        """If Content-Length is already set, don't overwrite it."""
        response = HttpResponse(
            headers={"Content-Length": "999"},
            body="Hi",
        )
        raw = response.to_bytes().decode()

        # Should keep the manually-set value, not auto-calculate.
        assert "Content-Length: 999\r\n" in raw

    def test_404_response(self) -> None:
        """A 404 Not Found response should have the correct status line."""
        response = HttpResponse(
            status=HttpStatus.NOT_FOUND,
            headers={"Content-Type": "text/plain"},
            body="Page not found",
        )
        raw = response.to_bytes().decode()

        assert "HTTP/1.1 404 Not Found\r\n" in raw
        assert "Page not found" in raw

    def test_empty_body(self) -> None:
        """A response with no body should still be valid HTTP."""
        response = HttpResponse(status=HttpStatus.NO_CONTENT)
        raw = response.to_bytes().decode()

        assert "HTTP/1.1 204 No Content\r\n" in raw
        # Should end with the blank line separating headers from (empty) body.
        assert "\r\n\r\n" in raw

    def test_to_bytes_returns_bytes(self) -> None:
        """to_bytes() should return bytes, not str."""
        response = HttpResponse(body="test")
        result = response.to_bytes()

        # `isinstance(obj, type)` is Python's `obj instanceof Type`.
        assert isinstance(result, bytes)

    def test_http_status_enum_values(self) -> None:
        """Verify the enum values match standard HTTP status codes."""
        assert HttpStatus.OK == 200
        assert HttpStatus.NOT_FOUND == 404
        assert HttpStatus.INTERNAL_SERVER_ERROR == 500

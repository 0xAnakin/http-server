# ──────────────────────────────────────────────────────────────
# test_middleware.py  —  Tests for the middleware pipeline
# ──────────────────────────────────────────────────────────────
#
# We test middleware by creating simple "spy" middlewares that record
# what happened, then asserting the order and results.
#
# KEY NEW CONCEPT — testing with side effects
#
#   Middleware has side effects (logging, error catching).  To test this,
#   we use a common pattern: collect evidence in a list, then assert
#   what was collected.
#
#   JS equivalent (Jest):
#     const log = [];
#     const mw = (req, next) => { log.push("before"); next(); log.push("after"); };
#     // ... run mw ...
#     expect(log).toEqual(["before", "after"]);
#
#   Python (pytest):
#     log: list[str] = []
#     def mw(req, next_handler): log.append("before"); ...
#     assert log == ["before", "after"]
#
# ──────────────────────────────────────────────────────────────

from http_server.middleware import (
    Handler,
    apply_middleware,
    error_middleware,
    logging_middleware,
)
from http_server.request import HttpRequest
from http_server.response import HttpResponse, HttpStatus

# ── Helpers ──────────────────────────────────────────────────


def _make_request(path: str = "/") -> HttpRequest:
    """Create a minimal GET request for testing."""
    return HttpRequest(method="GET", path=path, version="HTTP/1.1")


def _ok_handler(request: HttpRequest) -> HttpResponse:
    """A simple handler that always returns 200 OK."""
    return HttpResponse(status=HttpStatus.OK, body="OK")


def _boom_handler(request: HttpRequest) -> HttpResponse:
    """A handler that always raises an exception."""
    msg = "Something went wrong!"
    raise RuntimeError(msg)


# ──────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────


class TestApplyMiddleware:
    """Tests for the middleware pipeline builder."""

    def test_no_middleware_calls_handler_directly(self) -> None:
        """With an empty middleware list, the handler runs as-is."""
        pipeline = apply_middleware(_ok_handler, [])

        response = pipeline(_make_request())

        assert response.status == HttpStatus.OK
        assert response.body == "OK"

    def test_single_middleware_wraps_handler(self) -> None:
        """A single middleware should run before and after the handler."""
        log: list[str] = []

        def tracking_mw(
            request: HttpRequest,
            next_handler: Handler,
        ) -> HttpResponse:
            log.append("before")
            response = next_handler(request)
            log.append("after")
            return response

        pipeline = apply_middleware(_ok_handler, [tracking_mw])
        pipeline(_make_request())

        assert log == ["before", "after"]

    def test_middleware_order_is_correct(self) -> None:
        """Middlewares should run in the order they're listed."""
        log: list[str] = []

        def mw_a(
            request: HttpRequest,
            next_handler: Handler,
        ) -> HttpResponse:
            log.append("A-before")
            response = next_handler(request)
            log.append("A-after")
            return response

        def mw_b(
            request: HttpRequest,
            next_handler: Handler,
        ) -> HttpResponse:
            log.append("B-before")
            response = next_handler(request)
            log.append("B-after")
            return response

        pipeline = apply_middleware(_ok_handler, [mw_a, mw_b])
        pipeline(_make_request())

        # A is outermost, B is inner.  So:
        # A-before → B-before → handler → B-after → A-after
        assert log == ["A-before", "B-before", "B-after", "A-after"]

    def test_middleware_can_modify_response(self) -> None:
        """A middleware should be able to alter the response."""

        def add_header_mw(
            request: HttpRequest,
            next_handler: Handler,
        ) -> HttpResponse:
            response = next_handler(request)
            response.headers["X-Custom"] = "hello"
            return response

        pipeline = apply_middleware(_ok_handler, [add_header_mw])
        response = pipeline(_make_request())

        assert response.headers["X-Custom"] == "hello"


class TestLoggingMiddleware:
    """Tests for the built-in logging middleware."""

    def test_passes_response_through(self) -> None:
        """Logging middleware should not alter the response."""
        pipeline = apply_middleware(_ok_handler, [logging_middleware])

        response = pipeline(_make_request())

        assert response.status == HttpStatus.OK
        assert response.body == "OK"


class TestErrorMiddleware:
    """Tests for the built-in error-handling middleware."""

    def test_passes_normal_response_through(self) -> None:
        """When no error occurs, the response passes through unchanged."""
        pipeline = apply_middleware(_ok_handler, [error_middleware])

        response = pipeline(_make_request())

        assert response.status == HttpStatus.OK

    def test_catches_exception_returns_500(self) -> None:
        """When the handler throws, error middleware returns 500."""
        pipeline = apply_middleware(_boom_handler, [error_middleware])

        response = pipeline(_make_request())

        assert response.status == HttpStatus.INTERNAL_SERVER_ERROR
        assert "500" in response.body

    def test_full_pipeline_catches_errors(self) -> None:
        """Logging + error middleware together should handle errors gracefully."""
        pipeline = apply_middleware(_boom_handler, [logging_middleware, error_middleware])

        response = pipeline(_make_request())

        # Error middleware catches the exception, logging middleware
        # logs as usual and passes the 500 response through.
        assert response.status == HttpStatus.INTERNAL_SERVER_ERROR

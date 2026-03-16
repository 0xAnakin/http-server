# ──────────────────────────────────────────────────────────────
# test_router.py  —  Tests for the URL router
# ──────────────────────────────────────────────────────────────
#
# We test the router independently from the TCP server.  This is a
# "unit test" — it exercises one module in isolation, without starting
# a server or opening sockets.
#
# Testing strategy:
#   1. Create a Router and register some routes
#   2. Build fake HttpRequest objects and pass them to router.resolve()
#   3. Assert the returned HttpResponse has the right status/body
#
# This is like testing Express middleware by calling the handler directly
# with mock req/res objects, instead of spinning up the whole server.
# ──────────────────────────────────────────────────────────────

from http_server.request import HttpRequest
from http_server.response import HttpResponse, HttpStatus
from http_server.router import Router

# ── Helper: a minimal request object ─────────────────────────
# Instead of parsing raw bytes, we create HttpRequest directly.
# This keeps tests fast and focused on the router logic.


def _make_request(method: str = "GET", path: str = "/") -> HttpRequest:
    """Create a minimal HttpRequest for testing."""
    return HttpRequest(method=method, path=path, version="HTTP/1.1")


# ── Helper: a simple handler function ────────────────────────
# A handler is just a function: HttpRequest → HttpResponse.
# We define a few here so we can register them in our test router.


def _hello_handler(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=HttpStatus.OK, body="Hello!")


def _about_handler(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=HttpStatus.OK, body="About page")


def _post_handler(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=HttpStatus.CREATED, body="Created")


# ──────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────


class TestRouter:
    """Tests for the Router class."""

    def test_resolve_registered_route(self) -> None:
        """A registered route should return the handler's response."""
        router = Router()
        router.add_route("GET", "/", _hello_handler)

        response = router.resolve(_make_request("GET", "/"))

        assert response.status == HttpStatus.OK
        assert response.body == "Hello!"

    def test_resolve_multiple_routes(self) -> None:
        """Different paths should invoke different handlers."""
        router = Router()
        router.add_route("GET", "/", _hello_handler)
        router.add_route("GET", "/about", _about_handler)

        home_resp = router.resolve(_make_request("GET", "/"))
        about_resp = router.resolve(_make_request("GET", "/about"))

        assert home_resp.body == "Hello!"
        assert about_resp.body == "About page"

    def test_resolve_unknown_path_returns_404(self) -> None:
        """An unregistered path should return a 404 response."""
        router = Router()
        router.add_route("GET", "/", _hello_handler)

        response = router.resolve(_make_request("GET", "/nope"))

        assert response.status == HttpStatus.NOT_FOUND
        assert "404" in response.body

    def test_resolve_wrong_method_returns_404(self) -> None:
        """A registered path but wrong method should return 404."""
        router = Router()
        router.add_route("GET", "/", _hello_handler)

        # POST / is NOT registered, only GET /
        response = router.resolve(_make_request("POST", "/"))

        assert response.status == HttpStatus.NOT_FOUND

    def test_method_is_case_insensitive(self) -> None:
        """Route matching should be case-insensitive for the HTTP method."""
        router = Router()
        router.add_route("get", "/", _hello_handler)

        # Request comes in with uppercase "GET" (as it normally does in HTTP).
        response = router.resolve(_make_request("GET", "/"))

        assert response.status == HttpStatus.OK
        assert response.body == "Hello!"

    def test_different_methods_same_path(self) -> None:
        """GET /data and POST /data should route to different handlers."""
        router = Router()
        router.add_route("GET", "/data", _hello_handler)
        router.add_route("POST", "/data", _post_handler)

        get_resp = router.resolve(_make_request("GET", "/data"))
        post_resp = router.resolve(_make_request("POST", "/data"))

        assert get_resp.status == HttpStatus.OK
        assert post_resp.status == HttpStatus.CREATED

    def test_404_includes_path_info(self) -> None:
        """The 404 response should mention the path that wasn't found."""
        router = Router()

        response = router.resolve(_make_request("GET", "/missing"))

        assert "/missing" in response.body

    def test_empty_router_returns_404(self) -> None:
        """A router with no routes should always return 404."""
        router = Router()

        response = router.resolve(_make_request("GET", "/"))

        assert response.status == HttpStatus.NOT_FOUND

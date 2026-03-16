# ──────────────────────────────────────────────────────────────
# router.py  —  URL routing (mapping paths → handler functions)
# ──────────────────────────────────────────────────────────────
#
# Right now every request gets the same "Hello, World!" response.
# A router lets us map different URL paths to different handler
# functions, just like Express:
#
#   JS (Express):
#     app.get("/", homeHandler);
#     app.get("/about", aboutHandler);
#     // 404 fallback is automatic
#
#   Python (ours):
#     router = Router()
#     router.add_route("GET", "/", home_handler)
#     router.add_route("GET", "/about", about_handler)
#     response = router.resolve(request)
#
# KEY NEW CONCEPT — Callable type hint
#
#   In JS, any function is just "a function". TypeScript adds types:
#     type Handler = (req: HttpRequest) => HttpResponse;
#
#   Python has the same idea using `Callable` from the `collections.abc`
#   module (or `typing`):
#     Handler = Callable[[HttpRequest], HttpResponse]
#
#   This reads as: "a callable that takes an HttpRequest and returns
#   an HttpResponse" — exactly like a TypeScript function type.
#
# KEY NEW CONCEPT — type aliases
#
#   In TypeScript you write:
#     type Handler = (req: HttpRequest) => HttpResponse;
#
#   In Python (3.12+) there's a `type` statement for the same thing:
#     type Handler = Callable[[HttpRequest], HttpResponse]
#
#   We use an older style that also works:
#     Handler = Callable[[HttpRequest], HttpResponse]
#
#   This is just a name for a complex type — it makes type hints
#   more readable. The type alias itself doesn't do anything at runtime.
#
# KEY NEW CONCEPT — tuple as a dict key
#
#   In JS, objects can only have string (or Symbol) keys.
#   In Python, dict keys can be any "hashable" (immutable) type.
#   Tuples are immutable, so they work as dict keys:
#
#     routes = {
#         ("GET", "/"): home_handler,
#         ("GET", "/about"): about_handler,
#     }
#     handler = routes[("GET", "/")]
#
#   This lets us look up a handler by BOTH method and path in one step.
#   JS equivalent would require a nested object or a Map with string keys:
#     routes.get("GET:/")
#
# ──────────────────────────────────────────────────────────────

from collections.abc import Callable  # for typing function signatures

from http_server.request import HttpRequest
from http_server.response import HttpResponse, HttpStatus

# Type alias for a handler function.
# A handler takes an HttpRequest and returns an HttpResponse.
# JS equivalent: `type Handler = (req: HttpRequest) => HttpResponse;`
Handler = Callable[[HttpRequest], HttpResponse]


class Router:
    """
    A simple URL router that maps (method, path) pairs to handler functions.

    Usage:
        router = Router()
        router.add_route("GET", "/", home_handler)
        router.add_route("GET", "/about", about_handler)

        response = router.resolve(request)

    JS Express equivalent:
        const app = express();
        app.get("/", homeHandler);
        app.get("/about", aboutHandler);
    """

    def __init__(self) -> None:
        """
        Initialize an empty route table.

        `self._routes` is a dict mapping (method, path) tuples to handlers.
        The underscore prefix `_` is a Python convention meaning "private" —
        it's a hint to other developers that this attribute shouldn't be
        accessed directly from outside the class.

        JS equivalent:
            class Router {
                constructor() {
                    this._routes = new Map();  // Map<string, Handler>
                }
            }

        NOTE: Python has no real private/public enforcement (no `private`
        keyword like in TS/Java). The `_` is just a convention — you CAN
        still access `router._routes`, but you SHOULDN'T.
        """
        self._routes: dict[tuple[str, str], Handler] = {}

    def add_route(self, method: str, path: str, handler: Handler) -> None:
        """
        Register a handler for a specific HTTP method + URL path.

        Parameters
        ----------
        method : str
            The HTTP method — "GET", "POST", etc.
            Stored in uppercase for consistent matching.
        path : str
            The URL path — "/", "/about", "/health", etc.
        handler : Handler
            A function that takes an HttpRequest and returns an HttpResponse.

        JS Express equivalent:
            app.get("/about", handler);    // method is implicit ("GET")
            app.post("/login", handler);   // method is implicit ("POST")

        Our API is more explicit — you pass the method as a string:
            router.add_route("GET", "/about", handler)
        """
        # `.upper()` normalizes the method to uppercase. So if someone passes
        # "get", it becomes "GET" — making matching case-insensitive.
        # JS equivalent: `method.toUpperCase()`
        self._routes[(method.upper(), path)] = handler

    def resolve(self, request: HttpRequest) -> HttpResponse:
        """
        Find the right handler for a request and call it.

        Looks up (request.method, request.path) in the route table.
        If found → calls the handler and returns its response.
        If not found → returns a 404 Not Found response.

        Parameters
        ----------
        request : HttpRequest
            The parsed HTTP request (from our request parser).

        Returns
        -------
        HttpResponse
            The response from the matched handler, or a 404.

        JS Express equivalent:
            // Express does this internally — when a request comes in,
            // it walks through registered routes looking for a match.
            // If none match, it sends a default 404.
        """
        # Look up the handler using (method, path) as the key.
        # `dict.get(key, default)` returns the default if not found.
        # Here the default is None — meaning "no route matched".
        #
        # JS equivalent:
        #   const handler = routes.get(`${req.method}:${req.path}`) ?? null;
        handler = self._routes.get((request.method.upper(), request.path))

        if handler is not None:
            # Found a matching route — call the handler with the request.
            # `handler(request)` invokes the function stored in the dict.
            # It's like `handler(req)` in Express middleware.
            return handler(request)

        # ── No route matched — return 404 ────────────────────
        # This is our fallback, like Express's default 404 handler.
        return HttpResponse(
            status=HttpStatus.NOT_FOUND,
            headers={"Content-Type": "text/plain"},
            body=f"404 Not Found: {request.method} {request.path}",
        )

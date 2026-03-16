# ──────────────────────────────────────────────────────────────
# middleware.py  —  Middleware pipeline
# ──────────────────────────────────────────────────────────────
#
# Middleware are functions that wrap around request handling.  They
# can inspect/modify the request BEFORE it reaches the handler, and
# inspect/modify the response AFTER the handler runs.
#
# If you've used Express, you already know middleware:
#
#   JS (Express):
#     app.use((req, res, next) => {
#         console.log(`${req.method} ${req.url}`);
#         next();                    // call the next middleware/handler
#     });
#
# Express middleware calls `next()` to pass control forward.  Our design
# is slightly different — instead of `next()`, each middleware receives
# the NEXT function as a parameter and calls it explicitly:
#
#   Python (ours):
#     def logging_middleware(request, next_handler):
#         print(f"{request.method} {request.path}")
#         response = next_handler(request)   # ← this IS "next()"
#         return response
#
# This is called the "onion model" (or "Russian doll" model):
#
#   Request comes in  ──►  Middleware A  ──►  Middleware B  ──►  Handler
#   Response goes out ◄──  Middleware A  ◄──  Middleware B  ◄──  Handler
#
#   Each middleware wraps the next one, like layers of an onion.
#   The request passes THROUGH each layer going in, and the response
#   passes THROUGH each layer going back out.
#
#   JS frameworks that use this model: Koa, Hono, and Express (roughly).
#
# KEY NEW CONCEPT — higher-order functions
#
#   A higher-order function is a function that takes a function as an
#   argument, or returns a function as its result (or both).
#
#   JS:  array.map(x => x * 2)     // map takes a function
#        const add = (a) => (b) => a + b;  // returns a function
#
#   Our middleware system is built on higher-order functions:
#   - A Middleware takes a handler function and returns a NEW handler function
#   - Each middleware "wraps" the next handler by calling it inside its own logic
#
#   This pattern is called "function composition" — building a complex
#   function by combining simpler ones.  It's very common in Python
#   (decorators are syntactic sugar for it).
#
# KEY NEW CONCEPT — closures (same as JS!)
#
#   When `apply_middleware` creates the `wrapped` function inside a loop,
#   that function "closes over" the `mw` variable — it remembers it even
#   after the loop moves on.  This is identical to JS closures:
#
#   JS:
#     function makeGreeter(name) {
#         return () => `Hello, ${name}!`;  // closes over `name`
#     }
#
#   Python:
#     def make_greeter(name):
#         def greet():
#             return f"Hello, {name}!"     # closes over `name`
#         return greet
#
# ──────────────────────────────────────────────────────────────

import time  # for measuring request duration (built-in)
from collections.abc import Callable

from http_server.request import HttpRequest
from http_server.response import HttpResponse, HttpStatus

# ──────────────────────────────────────────────────────────────
# Type aliases
# ──────────────────────────────────────────────────────────────
#
# We define two type aliases to keep signatures readable:
#
# `Handler` — a function that takes a request and returns a response.
#   JS equivalent: `type Handler = (req: HttpRequest) => HttpResponse;`
#
# `Middleware` — a function that takes a request AND a next-handler,
#   and returns a response.  It can do work before/after calling next.
#   JS equivalent: `type Middleware = (req: HttpRequest, next: Handler) => HttpResponse;`
Handler = Callable[[HttpRequest], HttpResponse]
Middleware = Callable[[HttpRequest, Handler], HttpResponse]


def apply_middleware(handler: Handler, middlewares: list[Middleware]) -> Handler:
    """
    Wrap a handler with a list of middlewares, building the onion.

    Middlewares are applied in order — the FIRST middleware in the list
    is the OUTERMOST layer (runs first on request, last on response).

    Parameters
    ----------
    handler : Handler
        The core handler (e.g. router.resolve) to wrap.
    middlewares : list[Middleware]
        The middleware functions to apply, in order.

    Returns
    -------
    Handler
        A new handler that runs all middlewares around the original.

    Example
    -------
    JS equivalent:
        // Express does this internally when you call app.use():
        // It builds a chain of functions, each calling the next.
        const pipeline = [loggingMW, errorMW].reduce(
            (next, mw) => (req) => mw(req, next),
            handler
        );

    Python:
        pipeline = apply_middleware(router.resolve, [logging_mw, error_mw])
        response = pipeline(request)  # runs: logging → error → router
    """
    # Start with the core handler (the innermost layer of the onion).
    current: Handler = handler

    # Wrap it with each middleware, from LAST to FIRST.
    # We reverse so that the first middleware in the list becomes the
    # outermost layer — it runs first on incoming requests.
    #
    # `reversed()` returns an iterator that goes backwards through the list.
    # JS equivalent: `middlewares.slice().reverse().forEach(...)`
    #
    # Without reversing, the LAST middleware would run first, which is
    # counterintuitive.
    for mw in reversed(middlewares):
        # We need to capture `mw` and `current` in a closure.
        # Python closures in loops can be tricky — the variable `mw` would
        # reference the LAST value of the loop if we're not careful.
        #
        # Solution: use a default argument `mw=mw, inner=current` to capture
        # the CURRENT value at each step (Python evaluates default args once
        # at function definition time, not at call time).
        #
        # JS equivalent of the gotcha:
        #   for (var i = 0; i < 3; i++) {
        #       setTimeout(() => console.log(i), 100);  // prints 3, 3, 3!
        #   }
        #   // Fix: use `let` instead of `var`, or an IIFE.
        #   // Python fix: default argument capture.

        def make_wrapped(
            mw: Middleware = mw,
            inner: Handler = current,
        ) -> Handler:
            """A single layer of the onion — calls mw with inner as next."""

            # Return a NEW handler that calls this middleware with `inner`
            # as the next handler.  When `mw` calls `next_handler(request)`,
            # it's calling `inner` — which might be another middleware, or
            # the final handler.
            def wrapped(request: HttpRequest) -> HttpResponse:
                return mw(request, inner)

            return wrapped

        current = make_wrapped()

    return current


# ──────────────────────────────────────────────────────────────
# Built-in middlewares
# ──────────────────────────────────────────────────────────────


def logging_middleware(request: HttpRequest, next_handler: Handler) -> HttpResponse:
    """
    Log every request and response — like Morgan in Express.

    Prints:
        → GET /about
        ← 200 OK (3.2ms)

    JS (Express + Morgan):
        app.use(morgan("dev"));
        // Output: GET /about 200 3.215 ms

    Parameters
    ----------
    request : HttpRequest
        The incoming request.
    next_handler : Handler
        The next function in the chain (could be another middleware
        or the final route handler).

    Returns
    -------
    HttpResponse
        The response from the next handler (passed through unchanged).
    """
    # ── BEFORE the handler runs (request phase) ──────────────
    # `time.perf_counter()` returns a high-resolution timestamp in seconds.
    # JS equivalent: `performance.now()` (but that's in milliseconds).
    start = time.perf_counter()
    print(f"  → {request.method} {request.path}")

    # ── Call the next handler ────────────────────────────────
    # This is the `next()` call in Express.  Everything below this line
    # runs AFTER the handler (and any inner middlewares) have finished.
    response = next_handler(request)

    # ── AFTER the handler runs (response phase) ──────────────
    # Calculate how long the handler took.
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  ← {response.status} ({elapsed_ms:.1f}ms)")

    # Pass the response through unchanged.
    return response


def error_middleware(request: HttpRequest, next_handler: Handler) -> HttpResponse:
    """
    Catch unhandled exceptions and return a 500 Internal Server Error.

    Without this, an exception in a handler would crash the connection
    handler and possibly leave the client hanging.

    JS (Express):
        app.use((err, req, res, next) => {
            console.error(err.stack);
            res.status(500).send("Internal Server Error");
        });

    NOTE: Express has a special 4-argument error handler. In our design,
    we just wrap the call in a try/except — simpler and more Pythonic.

    Parameters
    ----------
    request : HttpRequest
        The incoming request.
    next_handler : Handler
        The next function in the chain.

    Returns
    -------
    HttpResponse
        Either the normal response, or a 500 error response.
    """
    try:
        return next_handler(request)
    except Exception as exc:
        # `Exception` is the base class for most errors in Python.
        # JS equivalent: `catch (err) { ... }`
        #
        # We log the error for debugging, then return a clean 500 response
        # instead of crashing.
        print(f"  ❌ Error handling {request.method} {request.path}: {exc}")
        return HttpResponse(
            status=HttpStatus.INTERNAL_SERVER_ERROR,
            headers={"Content-Type": "text/plain"},
            body="500 Internal Server Error",
        )

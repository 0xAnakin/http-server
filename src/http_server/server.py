# ──────────────────────────────────────────────────────────────
# server.py  —  The async HTTP server (step 2: TCP listener)
# ──────────────────────────────────────────────────────────────
#
# NEW IN THIS STEP:
#   We replace the placeholder with a real TCP server that:
#   1. Listens on a port for incoming TCP connections
#   2. Reads raw data from each client
#   3. Sends back a hardcoded HTTP response
#   4. Closes the connection
#
# KEY NEW CONCEPT — asyncio.start_server()
#
#   This is Python's high-level API for creating a TCP server.
#   It's the equivalent of Node's `net.createServer()`:
#
#   JS (Node):
#     const server = net.createServer((socket) => {
#         socket.on('data', (data) => { ... });
#         socket.write('HTTP/1.1 200 OK\r\n...');
#         socket.end();
#     });
#     server.listen(8000);
#
#   Python (asyncio):
#     async def handle_client(reader, writer):
#         data = await reader.read(1024)
#         writer.write(b"HTTP/1.1 200 OK\r\n...")
#         writer.close()
#     server = await asyncio.start_server(handle_client, host, port)
#
#   The big difference: in Node you register event callbacks ('data', 'end'),
#   while in Python you get a reader/writer pair and use `await` directly.
#   It's more sequential — reads like synchronous code, but is fully async.
#
# KEY NEW CONCEPT — StreamReader / StreamWriter
#
#   asyncio gives you two objects per connection:
#   • StreamReader — reads data FROM the client (like socket.on('data'))
#   • StreamWriter — writes data TO the client (like socket.write())
#
#   These are thin wrappers around the raw TCP socket. They handle buffering
#   and backpressure for you — just like Node streams.
#
# KEY NEW CONCEPT — bytes vs strings (b"..." prefix)
#
#   In JS, strings and network data are somewhat interchangeable (Buffer ↔ string).
#   In Python, there's a strict separation:
#   • str   = text (Unicode).    Written as "hello"
#   • bytes = raw binary data.   Written as b"hello"
#
#   TCP sockets deal in bytes, not strings. So when we write to a socket,
#   we use b"HTTP/1.1 200 OK\r\n..." (note the `b` prefix).
#
#   To convert between them:
#   • str → bytes:   "hello".encode("utf-8")    (like Buffer.from("hello"))
#   • bytes → str:   b"hello".decode("utf-8")   (like buffer.toString())
#
# KEY NEW CONCEPT — `async with` (async context manager)
#
#   In JS you might write:
#     const server = createServer();
#     try { ... } finally { server.close(); }
#
#   Python has a cleaner pattern called a "context manager" using `with`:
#     with open("file.txt") as f:
#         f.read()
#     # f is automatically closed here — no need for try/finally
#
#   `async with` is the same but for async resources. We use it to ensure
#   the server is properly shut down when we exit.
# ──────────────────────────────────────────────────────────────

import asyncio  # Python's built-in async I/O library (like Node's event loop)
from pathlib import Path  # object-oriented file paths (like Node's `path` module)

from http_server.request import HttpRequest, parse_request  # our HTTP request parser
from http_server.response import HttpResponse, HttpStatus  # our HTTP response builder
from http_server.router import Router  # our URL router
from http_server.static import serve_static  # our static file server

# ──────────────────────────────────────────────────────────────
# Static file directory
# ──────────────────────────────────────────────────────────────
#
# `Path(__file__)` gives us the path to THIS file (server.py).
# `.parent` goes up one level (the http_server package dir).
# `.parent.parent` goes up again (the src dir).
# `.parent.parent.parent` reaches the project root.
#
# Then `/ "public"` appends the "public" folder.
#
# JS equivalent:
#   const STATIC_DIR = path.join(__dirname, "..", "..", "..", "public");
#
# NOTE: `__file__` is a special Python variable that holds the path
# to the current source file — like `__filename` in Node (or
# `import.meta.url` in ES modules).
# ──────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent.parent.parent / "public"

# ──────────────────────────────────────────────────────────────
# Route handlers — one function per URL path
# ──────────────────────────────────────────────────────────────
#
# Each handler is a plain function that takes an HttpRequest and returns
# an HttpResponse.  This is similar to Express route handlers:
#
#   JS (Express):
#     app.get("/", (req, res) => { res.send("Hello!"); });
#
#   Python (ours):
#     def home(request: HttpRequest) -> HttpResponse:
#         return HttpResponse(body="Hello!")
#
# The key difference: Express handlers receive BOTH req and res and mutate
# res in-place. Our handlers receive req and RETURN a new response object.
# This is a more "functional" style — no mutation, just input → output.
# ──────────────────────────────────────────────────────────────


def home(request: HttpRequest) -> HttpResponse:
    """Handler for GET / — serve the static index.html page."""
    # Instead of a plain-text response, serve the HTML file from public/.
    # This delegates to the static file server we just built.
    return serve_static(request, STATIC_DIR)


def about(request: HttpRequest) -> HttpResponse:
    """Handler for GET /about — an about page."""
    return HttpResponse(
        status=HttpStatus.OK,
        headers={"Content-Type": "text/plain"},
        body="This is an async HTTP server built from scratch in Python.",
    )


def health(request: HttpRequest) -> HttpResponse:
    """Handler for GET /health — a health-check endpoint."""
    # Health-check endpoints are common in production. Load balancers
    # and monitoring tools hit this to verify the server is alive.
    # JS equivalent: `app.get("/health", (req, res) => res.json({ status: "ok" }));`
    return HttpResponse(
        status=HttpStatus.OK,
        headers={"Content-Type": "application/json"},
        body='{"status": "ok"}',
    )


# ──────────────────────────────────────────────────────────────
# Create the router and register routes
# ──────────────────────────────────────────────────────────────
#
# This code runs ONCE when the module is first imported.
# Module-level code in Python is like top-level code in a JS file —
# it executes when the file is loaded.
#
#   JS equivalent:
#     const router = new Router();
#     router.get("/", home);
#     router.get("/about", about);
#     export { router };
# ──────────────────────────────────────────────────────────────

router = Router()
router.add_route("GET", "/", home)
router.add_route("GET", "/about", about)
router.add_route("GET", "/health", health)


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """
    Handle a single TCP client connection.

    This function is called ONCE for each new connection — it's the callback
    you'd pass to `net.createServer(callback)` in Node.

    Parameters
    ----------
    reader : asyncio.StreamReader
        Reads data FROM the client.  Like `socket.on('data', ...)` in Node,
        but instead of events, you `await reader.read()`.
    writer : asyncio.StreamWriter
        Writes data TO the client.  Like `socket.write(...)` in Node.
    """
    # ── 1. Get info about who connected ──────────────────────
    # `writer.get_extra_info("peername")` returns the client's (ip, port) tuple.
    # In Node this would be: `socket.remoteAddress` and `socket.remotePort`.
    #
    # A "tuple" is like a fixed-length, immutable array in JS:
    #   JS:     const addr = [ip, port];   // but you could mutate it
    #   Python: addr = (ip, port)          // immutable — can't change after creation
    addr = writer.get_extra_info("peername")
    print(f"📥 New connection from {addr}")

    # ── 2. Read the raw request data from the client ─────────
    # `await reader.read(4096)` reads UP TO 4096 bytes from the socket.
    # It returns a `bytes` object (not a string — remember, TCP deals in raw bytes).
    #
    # 4096 is just a buffer size — we'll read more intelligently later when
    # we parse HTTP headers properly. For now, one read is enough to grab
    # a simple request.
    #
    # JS equivalent:
    #   socket.on('data', (chunk) => { ... });
    #   // But here we await a single read instead of handling events.
    data: bytes = await reader.read(4096)

    # ── 3. Guard: bail out if the client already disconnected ─
    # When `reader.read()` returns empty bytes (b""), it means the client
    # closed the connection before sending anything (like a browser
    # pre-opening a speculative connection and then abandoning it).
    # No point building and sending a response — just clean up and exit.
    #
    # `not data` is truthy when data is b"" (empty bytes).
    # JS equivalent: `if (!data.length) { socket.destroy(); return; }`
    if not data:
        print(f"⚠️  Empty request from {addr}, closing connection.")
        writer.close()
        await writer.wait_closed()
        return  # early return — nothing else to do

    # ── 4. Parse the raw bytes into a structured request ───
    # Instead of manually splitting strings, we use our parser to get
    # a proper HttpRequest object with .method, .path, .headers, etc.
    # This is like going from raw `req.socket.on('data')` to Express's
    # `req.method`, `req.path`, `req.headers` — but we built the parser.
    request = parse_request(data)
    print(f"📨 Request: {request.method} {request.path} {request.version}")

    # Log the headers too — useful for debugging.
    # `request.headers.items()` returns key-value pairs, like Object.entries() in JS:
    #   JS:     Object.entries(headers).forEach(([k, v]) => ...)
    #   Python: for k, v in headers.items(): ...
    for key, value in request.headers.items():
        print(f"   {key}: {value}")

    # ── 5. Route the request to the correct handler ──────────
    # First, try the explicit routes (/, /about, /health).
    # If no route matches, fall back to static file serving.
    #
    # This is exactly how Express works:
    #   app.get("/about", aboutHandler);        // explicit routes first
    #   app.use(express.static("public"));       // then static files
    #   // If neither matches, Express sends 404.
    #
    # We check if the router found a handler. If the response is 404,
    # we try serving a static file before giving up.
    response = router.resolve(request)

    # If the router returned 404, try static files as a fallback.
    # This lets URLs like /style.css serve files from public/style.css.
    if response.status == HttpStatus.NOT_FOUND:
        static_response = serve_static(request, STATIC_DIR)
        # Only use the static response if the file was actually found.
        if static_response.status != HttpStatus.NOT_FOUND:
            response = static_response

    # ── 6. Send the response back to the client ──────────────
    # `response.to_bytes()` serializes the HttpResponse into raw HTTP bytes.
    # `writer.write()` buffers the data to send (like `socket.write()` in Node).
    writer.write(response.to_bytes())

    # `await writer.drain()` flushes the write buffer — ensures all data is
    # actually sent over the network before we continue.
    # JS doesn't have an exact equivalent — Node auto-flushes, but the closest
    # concept is waiting for the 'drain' event on a writable stream.
    await writer.drain()

    # ── 7. Close the connection ──────────────────────────────
    # `writer.close()` starts closing the socket (like `socket.end()` in Node).
    # `await writer.wait_closed()` waits until it's fully closed.
    print(f"📤 Response sent to {addr}, closing connection.")
    writer.close()
    await writer.wait_closed()


async def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Start the async HTTP server — listens for TCP connections.

    Parameters
    ----------
    host : str
        The network interface to bind to.
        "127.0.0.1" = localhost only.
        "0.0.0.0"   = all interfaces.
    port : int
        The TCP port number.
    """
    # ── Create the TCP server ────────────────────────────────
    # `asyncio.start_server()` is the Python equivalent of:
    #
    #   const server = net.createServer(handleClient);
    #   server.listen(port, host);
    #
    # It returns a Server object that is already listening.
    # `handle_client` will be called for EACH new connection.
    server = await asyncio.start_server(handle_client, host, port)

    # ── Log the listening address ────────────────────────────
    # `server.sockets` is a list of socket objects the server is listening on.
    # We grab the first one's address for logging.
    # In JS: `server.address()` returns { address, port, family }.
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"🚀 http-server v0.1.0 listening on {addrs}")
    print("   Press Ctrl+C to stop.\n")

    # ── Serve forever ────────────────────────────────────────
    # `async with server` ensures clean shutdown when we exit.
    # Inside, `server.serve_forever()` blocks (awaits) indefinitely —
    # it processes incoming connections until Ctrl+C or a shutdown signal.
    #
    # JS equivalent:
    #   // Node servers run forever by default once .listen() is called.
    #   // There's no explicit "serve forever" — the event loop just keeps going.
    #   // Python requires this explicit call because asyncio.run() would
    #   // otherwise exit as soon as start_server() returns.
    async with server:
        await server.serve_forever()


def main() -> None:
    """
    Synchronous entry point that boots the async event loop.

    `asyncio.run()` does three things:
      1. Creates a brand-new event loop
      2. Runs the coroutine until it completes (or Ctrl+C)
      3. Cleans up (closes the loop, cancels pending tasks)

    JS equivalent: `(async () => { await startServer(); })();`
    """
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        # Ctrl+C raises KeyboardInterrupt in Python (like process.on('SIGINT') in Node).
        # We catch it here so the program exits cleanly without an ugly traceback.
        print("\n👋 Server stopped.")

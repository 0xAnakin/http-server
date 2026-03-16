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

from http_server.request import parse_request  # our HTTP request parser
from http_server.response import HttpResponse, HttpStatus  # our HTTP response builder


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

    # ── 5. Build a response using our HttpResponse builder ───
    # Instead of assembling raw strings, we use a structured object.
    # This is like going from:
    #   res.writeHead(200); res.end("Hello");
    # to Express's:
    #   res.status(200).type("text/plain").send("Hello, World!");
    #
    # Content-Length and Connection headers are set automatically
    # by HttpResponse.to_bytes() — we don't have to manage them.
    response = HttpResponse(
        status=HttpStatus.OK,
        headers={"Content-Type": "text/plain"},
        body="Hello, World!",
    )

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

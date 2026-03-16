# ──────────────────────────────────────────────────────────────
# test_server.py  —  Tests for our HTTP server
# ──────────────────────────────────────────────────────────────
#
# Pytest discovers tests by simple naming conventions:
#   • Files must start with `test_` (like test_server.py)
#   • Functions must start with `test_` (like def test_version())
#   • No need to register or import a test runner — just name things right.
#
# This is simpler than Jest, where you need `.test.js` or `.spec.js`.
# Pytest also doesn't need `describe()` / `it()` blocks — plain functions work.
#
# KEY PYTHON CONCEPT — `assert`
#   Python has a built-in `assert` statement:
#       assert expression, "optional error message"
#   If the expression is falsy, it raises an AssertionError.
#   Pytest hooks into this and gives you rich, readable diffs when asserts fail
#   (no need for expect().toBe() or assertEqual() — just plain `assert`).
#
#   JS equivalent:   expect(actual).toBe(expected)
#   Python (pytest):  assert actual == expected
#
# NEW IN THIS STEP — testing an async server
#
#   To test a server, we:
#   1. Start the server on a random port (port 0 = "OS picks an available port")
#   2. Connect to it as a client and send a request
#   3. Read the response and assert it's correct
#   4. Shut down the server
#
#   This is like using supertest in Node/Express, but done manually with
#   raw asyncio TCP connections (since we're learning the low level).
# ──────────────────────────────────────────────────────────────

import asyncio  # needed to connect to the server and run async tests

from http_server import __version__  # import the version from our package
from http_server.server import handle_client  # import our connection handler


def test_version() -> None:
    """Ensure the package version is what we expect."""
    assert __version__ == "0.1.0"


def test_server_responds_with_hello_world() -> None:
    """
    Start a real TCP server, connect to it, and verify the HTTP response.

    This is an integration test — it exercises the full flow:
    client connects → sends request → server replies → client reads response.
    """

    async def _run_test() -> None:
        # ── 1. Start the server on a random available port ───
        # Port 0 tells the OS: "pick any free port for me."
        # This prevents port conflicts when running tests.
        # JS equivalent: `server.listen(0)` then `server.address().port`
        server = await asyncio.start_server(handle_client, "127.0.0.1", 0)

        # Get the actual port the OS assigned.
        # `server.sockets[0].getsockname()` returns a (host, port) tuple.
        # The `[1]` grabs the port from the tuple.
        #   JS equivalent: `server.address().port`
        addr = server.sockets[0].getsockname()
        port: int = addr[1]

        # ── 2. Connect to the server as a TCP client ─────────
        # `asyncio.open_connection()` creates a client TCP connection.
        # JS equivalent: `net.createConnection({ port })`
        # It returns the same (reader, writer) pair as the server handler.
        reader, writer = await asyncio.open_connection("127.0.0.1", port)

        # ── 3. Send a minimal HTTP request ───────────────────
        # A valid HTTP/1.1 request needs at minimum:
        #   GET / HTTP/1.1\r\n
        #   Host: localhost\r\n
        #   \r\n                   ← empty line = end of headers
        request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        writer.write(request)
        await writer.drain()

        # ── 4. Read the server's response ────────────────────
        # Read up to 4096 bytes. `await reader.read(4096)` returns bytes.
        response_bytes: bytes = await reader.read(4096)
        # Convert bytes → string so we can inspect it.
        response = response_bytes.decode()

        # ── 5. Assert the response is a valid HTTP 200 ──────
        # `in` checks if a substring exists — like JS `str.includes()`:
        #   JS:     response.includes("200 OK")
        #   Python: "200 OK" in response
        assert "HTTP/1.1 200 OK" in response
        # The home route now serves public/index.html (static file),
        # so we check for HTML content instead of "Hello, World!".
        assert "Welcome to http-server" in response
        assert "Content-Type: text/html" in response

        # ── 6. Clean up ─────────────────────────────────────
        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()

    # `asyncio.run()` executes our async test function.
    # We need this because the test function itself is sync (def, not async def).
    # Later we can use pytest-asyncio to avoid this wrapper.
    asyncio.run(_run_test())

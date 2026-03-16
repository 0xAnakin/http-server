# ──────────────────────────────────────────────────────────────
# test_static.py  —  Tests for the static file server
# ──────────────────────────────────────────────────────────────
#
# We test static file serving by creating temporary files in a temp
# directory, then calling `serve_static()` with fake requests.
#
# KEY NEW CONCEPT — tmp_path (pytest fixture)
#
#   Pytest provides a `tmp_path` fixture — a temporary directory that's
#   automatically created for each test and cleaned up afterwards.
#
#   JS equivalent: you'd use `os.tmpdir()` or a library like `tmp`:
#     const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "test-"));
#     // ... run test ...
#     fs.rmSync(tmpDir, { recursive: true });
#
#   In pytest, just add `tmp_path` as a parameter to your test function
#   and pytest fills it in automatically (that's dependency injection!).
#
# KEY NEW CONCEPT — fixtures (dependency injection for tests)
#
#   Pytest "fixtures" are functions that provide test data or setup.
#   If your test function has a parameter named `tmp_path`, pytest
#   recognizes it and injects a fresh Path to a temp directory.
#
#   It's like Jest's beforeEach, but more flexible — you declare what
#   you need as function parameters instead of setting up in beforeEach.
#
# ──────────────────────────────────────────────────────────────

from pathlib import Path

from http_server.request import HttpRequest
from http_server.response import HttpStatus
from http_server.static import get_mime_type, serve_static

# ── Helper ───────────────────────────────────────────────────


def _make_request(path: str = "/") -> HttpRequest:
    """Create a minimal GET request for testing."""
    return HttpRequest(method="GET", path=path, version="HTTP/1.1")


# ──────────────────────────────────────────────────────────────
# Tests for get_mime_type
# ──────────────────────────────────────────────────────────────


class TestGetMimeType:
    """Tests for the MIME type lookup function."""

    def test_html_file(self) -> None:
        assert get_mime_type(Path("index.html")) == "text/html; charset=utf-8"

    def test_css_file(self) -> None:
        assert get_mime_type(Path("style.css")) == "text/css; charset=utf-8"

    def test_js_file(self) -> None:
        assert get_mime_type(Path("app.js")) == "application/javascript; charset=utf-8"

    def test_png_file(self) -> None:
        assert get_mime_type(Path("logo.png")) == "image/png"

    def test_unknown_extension_returns_default(self) -> None:
        assert get_mime_type(Path("data.xyz")) == "application/octet-stream"

    def test_case_insensitive(self) -> None:
        """File extensions should be matched case-insensitively."""
        assert get_mime_type(Path("INDEX.HTML")) == "text/html; charset=utf-8"


# ──────────────────────────────────────────────────────────────
# Tests for serve_static
# ──────────────────────────────────────────────────────────────


class TestServeStatic:
    """Tests for static file serving."""

    def test_serves_existing_html_file(self, tmp_path: Path) -> None:
        """An existing HTML file should be served with 200 and correct type."""
        # Create a test file in the temp directory.
        # `write_text()` is like `fs.writeFileSync(path, content, "utf-8")`.
        (tmp_path / "hello.html").write_text("<h1>Hi</h1>")

        response = serve_static(_make_request("/hello.html"), tmp_path)

        assert response.status == HttpStatus.OK
        assert "<h1>Hi</h1>" in response.body
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"

    def test_serves_css_file(self, tmp_path: Path) -> None:
        """A CSS file should get the correct MIME type."""
        (tmp_path / "style.css").write_text("body { color: red; }")

        response = serve_static(_make_request("/style.css"), tmp_path)

        assert response.status == HttpStatus.OK
        assert "body { color: red; }" in response.body
        assert response.headers["Content-Type"] == "text/css; charset=utf-8"

    def test_serves_index_html_for_root_path(self, tmp_path: Path) -> None:
        """GET / should serve index.html by default."""
        (tmp_path / "index.html").write_text("<h1>Home</h1>")

        response = serve_static(_make_request("/"), tmp_path)

        assert response.status == HttpStatus.OK
        assert "<h1>Home</h1>" in response.body

    def test_returns_404_for_missing_file(self, tmp_path: Path) -> None:
        """A non-existent file should return 404."""
        response = serve_static(_make_request("/nope.html"), tmp_path)

        assert response.status == HttpStatus.NOT_FOUND

    def test_returns_404_for_directory(self, tmp_path: Path) -> None:
        """Requesting a directory (not a file) should return 404."""
        (tmp_path / "subdir").mkdir()

        response = serve_static(_make_request("/subdir"), tmp_path)

        assert response.status == HttpStatus.NOT_FOUND

    def test_blocks_path_traversal(self, tmp_path: Path) -> None:
        """Paths with '..' that escape the static dir should be blocked."""
        response = serve_static(_make_request("/../../../etc/passwd"), tmp_path)

        # Should return 400 (bad request) or 404 — NOT the file contents.
        assert response.status in (HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND)

    def test_serves_file_in_subdirectory(self, tmp_path: Path) -> None:
        """Files in subdirectories should be reachable."""
        sub = tmp_path / "css"
        sub.mkdir()
        (sub / "main.css").write_text("h1 { font-size: 2rem; }")

        response = serve_static(_make_request("/css/main.css"), tmp_path)

        assert response.status == HttpStatus.OK
        assert "h1 { font-size: 2rem; }" in response.body

# ──────────────────────────────────────────────────────────────
# static.py  —  Static file serving
# ──────────────────────────────────────────────────────────────
#
# This module serves files from a directory on disk — HTML, CSS, JS,
# images, etc.  It's the Python equivalent of Express's built-in
# static middleware:
#
#   JS (Express):
#     app.use(express.static("public"));
#     // Serves files from the "public" folder.
#     // GET /index.html  →  reads public/index.html from disk
#     // GET /style.css   →  reads public/style.css from disk
#
#   Python (ours):
#     static_handler = make_static_handler(Path("public"))
#     router.add_route("GET", "/style.css", static_handler)
#     // OR: we'll integrate it as a fallback in the router.
#
# KEY NEW CONCEPT — pathlib.Path
#
#   Python's `pathlib` module provides an object-oriented way to work with
#   file paths.  It's similar to Node's `path` module but more powerful:
#
#   JS (Node):
#     const fullPath = path.join(__dirname, "public", "index.html");
#     const exists   = fs.existsSync(fullPath);
#     const content  = fs.readFileSync(fullPath, "utf-8");
#
#   Python (pathlib):
#     full_path = Path("public") / "index.html"   # / operator joins paths!
#     exists    = full_path.exists()
#     content   = full_path.read_text()
#
#   The `/` operator is overloaded to join path segments — one of Python's
#   nicer tricks. `Path("public") / "index.html"` → `Path("public/index.html")`
#
# KEY NEW CONCEPT — reading files
#
#   JS:      fs.readFileSync("file.txt")           → Buffer
#            fs.readFileSync("file.txt", "utf-8")   → string
#
#   Python:  Path("file.txt").read_bytes()          → bytes
#            Path("file.txt").read_text()            → str
#
#   Or the older style (like fs.open → read → close):
#     with open("file.txt", "rb") as f:   # "rb" = read binary
#         content = f.read()
#
#   We use `read_bytes()` because we're serving the raw file content
#   over HTTP — and some files (images, fonts) aren't text.
#
# KEY NEW CONCEPT — security: path traversal attacks
#
#   If a client requests GET /../../etc/passwd, a naive server would
#   join that with the static directory and serve a system file!
#   This is called a "path traversal" or "directory traversal" attack.
#
#   We prevent this by using `.resolve()` to get the absolute path,
#   then checking that it's still inside our static directory.
#
#   JS equivalent:
#     const resolved = path.resolve(staticDir, requestedPath);
#     if (!resolved.startsWith(path.resolve(staticDir))) {
#         return res.status(403).send("Forbidden");
#     }
#
# KEY NEW CONCEPT — dict literal for MIME types
#
#   MIME types tell the browser what kind of file it's receiving.
#   We use a simple dict lookup by file extension — similar to the
#   `mime` npm package, but hand-rolled for learning.
#
# ──────────────────────────────────────────────────────────────

from pathlib import Path  # object-oriented filesystem paths (built-in)

from http_server.request import HttpRequest
from http_server.response import HttpResponse, HttpStatus

# ──────────────────────────────────────────────────────────────
# MIME type mapping (file extension → Content-Type)
# ──────────────────────────────────────────────────────────────
#
# When a browser receives a file, it needs to know what type it is.
# The Content-Type header tells it: "this is HTML", "this is CSS", etc.
#
# JS equivalent (using the `mime` npm package):
#   mime.getType("style.css")  →  "text/css"
#
# We roll our own with a simple dict:
MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

# The fallback MIME type when we don't recognize the extension.
# "application/octet-stream" means "raw binary data — download it".
# JS equivalent: `mime.getType("unknown") ?? "application/octet-stream"`
DEFAULT_MIME_TYPE = "application/octet-stream"


def get_mime_type(file_path: Path) -> str:
    """
    Look up the MIME type for a file based on its extension.

    Parameters
    ----------
    file_path : Path
        The file path to check.

    Returns
    -------
    str
        The MIME type string (e.g. "text/html; charset=utf-8").

    Examples
    --------
    >>> get_mime_type(Path("index.html"))
    'text/html; charset=utf-8'
    >>> get_mime_type(Path("photo.png"))
    'image/png'
    >>> get_mime_type(Path("data.bin"))
    'application/octet-stream'
    """
    # `file_path.suffix` returns the file extension including the dot.
    # JS equivalent: `path.extname("style.css")` → ".css"
    #
    # `.lower()` normalizes ".CSS" → ".css" for case-insensitive matching.
    return MIME_TYPES.get(file_path.suffix.lower(), DEFAULT_MIME_TYPE)


def serve_static(request: HttpRequest, static_dir: Path) -> HttpResponse:
    """
    Serve a static file from `static_dir` based on the request path.

    This is the core function — it takes a request like GET /style.css
    and tries to read `static_dir/style.css` from disk.

    Parameters
    ----------
    request : HttpRequest
        The parsed HTTP request. We use `request.path` to find the file.
    static_dir : Path
        The root directory to serve files from (e.g. Path("public")).

    Returns
    -------
    HttpResponse
        200 with file contents, or 404 if not found, or 403 if the path
        tries to escape the static directory.

    Security
    --------
    Prevents path traversal attacks by resolving the full path and checking
    it's still within `static_dir`.
    """
    # ── 1. Strip the leading "/" from the request path ───────
    # request.path is "/style.css" but we need "style.css" to join
    # with the static directory.
    #
    # `lstrip("/")` removes leading slashes.
    # JS equivalent: `requestPath.replace(/^\\/+/, "")`
    #
    # If the path is just "/", serve "index.html" as the default
    # (same convention as Express and most web servers).
    relative_path = request.path.lstrip("/")
    if not relative_path:
        relative_path = "index.html"

    # ── 2. Build the full file path ──────────────────────────
    # Path's `/` operator joins path segments:
    #   Path("public") / "style.css"  →  Path("public/style.css")
    # JS equivalent: `path.join(staticDir, relativePath)`
    file_path = static_dir / relative_path

    # ── 3. Security check: prevent path traversal ────────────
    # `.resolve()` turns relative paths into absolute ones and resolves
    # any ".." components:
    #   Path("public/../etc/passwd").resolve() → Path("/etc/passwd")
    #
    # We then check that the resolved path starts with the resolved
    # static directory. If it doesn't, someone is trying to escape.
    #
    # `is_relative_to()` returns True if the path is inside the given
    # directory. Added in Python 3.9.
    # JS equivalent:
    #   const resolved = path.resolve(staticDir, relativePath);
    #   if (!resolved.startsWith(path.resolve(staticDir))) { ... }
    resolved_path = file_path.resolve()
    resolved_dir = static_dir.resolve()

    if not resolved_path.is_relative_to(resolved_dir):
        # Someone tried something like GET /../../etc/passwd — block it.
        return HttpResponse(
            status=HttpStatus.BAD_REQUEST,
            headers={"Content-Type": "text/plain"},
            body="400 Bad Request: Invalid path",
        )

    # ── 4. Check if the file exists and is a file ────────────
    # `path.is_file()` returns True only if it exists AND is a regular file
    # (not a directory, not a symlink to a directory).
    # JS equivalent: `fs.existsSync(path) && fs.statSync(path).isFile()`
    if not resolved_path.is_file():
        return HttpResponse(
            status=HttpStatus.NOT_FOUND,
            headers={"Content-Type": "text/plain"},
            body=f"404 Not Found: {request.path}",
        )

    # ── 5. Read the file and determine its MIME type ─────────
    # `read_bytes()` reads the entire file as raw bytes.
    # We DON'T use `read_text()` because binary files (images, fonts)
    # would crash with a UnicodeDecodeError.
    #
    # JS equivalent: `fs.readFileSync(filePath)`  (returns Buffer)
    file_bytes: bytes = resolved_path.read_bytes()
    mime_type = get_mime_type(resolved_path)

    # ── 6. Build and return the response ─────────────────────
    # For text files (HTML, CSS, JS), we decode the bytes to a string
    # so HttpResponse.to_bytes() can re-encode them. For binary files
    # (images), we'd ideally send raw bytes — but our HttpResponse
    # currently uses a string body. For now, we decode with
    # latin-1 which maps every byte 0-255 to a character and back
    # losslessly (it's a 1-to-1 mapping, unlike UTF-8).
    #
    # NOTE: This is a known limitation. In a future step we could add
    # a `body_bytes` field to HttpResponse for true binary support.
    # For now, this works for text files and simple binary files.
    if mime_type.startswith("text/") or "json" in mime_type or "javascript" in mime_type:
        # Text files — decode as UTF-8 (the standard for web content).
        body = file_bytes.decode("utf-8")
    else:
        # Binary files — use latin-1 as a lossless byte↔char mapping.
        body = file_bytes.decode("latin-1")

    return HttpResponse(
        status=HttpStatus.OK,
        headers={"Content-Type": mime_type},
        body=body,
    )

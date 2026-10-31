"""The listener FM's phone sends its lots to ("Sync to Friday").

``GET /health`` answers ``ok`` (the phone's Test button). ``POST /lots`` with the shared token
in ``x-sync-token`` carries the lots feed as JSON; it is handed to ``on_push``, whose answer
goes back to the phone. Nothing is written to disk and nothing else is served.
"""

import hmac
import logging
import secrets
import socket
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

log = logging.getLogger(__name__)

TOKEN_HEADER = "x-sync-token"
MAX_BYTES = 64 * 1024 * 1024


def ensure_token(folder: Path) -> str:
    """The token kept in ``folder/token.txt``, made on first use."""
    path = folder / "token.txt"
    if path.is_file() and path.read_text(encoding="utf-8").strip():
        return path.read_text(encoding="utf-8").strip()
    folder.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    path.write_text(token, encoding="utf-8")
    return token


def lan_addresses() -> list[str]:
    """This PC's IPv4 addresses on the network, for typing into the phone."""
    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    except OSError:
        pass
    return sorted(address for address in found if not address.startswith("127."))


class FmReceiver:
    def __init__(
        self,
        *,
        token: str,
        on_push: Callable[[bytes], tuple[int, str]],
        host: str = "0.0.0.0",  # noqa: S104 (the phone is on the Wi-Fi)
        port: int = 8090,
    ) -> None:
        self.token = token
        self.on_push = on_push
        self.lock = threading.Lock()  # one push at a time
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (http.server's name)
                if self.path == "/health":
                    self._answer(200, "ok")
                else:
                    self._answer(404, "not found")

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/lots":
                    self._answer(404, "not found")
                    return
                given = self.headers.get(TOKEN_HEADER, "")
                if not hmac.compare_digest(given.encode(), receiver.token.encode()):
                    self._answer(401, "wrong token")
                    return
                try:
                    size = int(self.headers.get("content-length", ""))
                except ValueError:
                    self._answer(411, "length required")
                    return
                if not 0 < size <= MAX_BYTES:
                    self._answer(413, "too large")
                    return
                body = self.rfile.read(size)
                if len(body) < size:
                    self._answer(400, "the upload stopped early")
                    return
                self._answer(*receiver.receive(body))

            def _answer(self, status: int, text: str) -> None:
                body = text.encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "text/plain; charset=utf-8")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                log.info("fm push %s: " + format, self.client_address[0], *args)

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return self.server.server_address[1]

    def receive(self, body: bytes) -> tuple[int, str]:
        with self.lock:
            try:
                return self.on_push(body)
            except Exception:
                log.exception("importing FM's lots failed")
                return 500, "Friday received the lots, but the import failed"

    def start(self) -> None:
        self.thread = threading.Thread(
            target=self.server.serve_forever, name="fm-receiver", daemon=True
        )
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

"""Local HTTP server running inside Blender on localhost:9876."""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import executor, capture

_server = None
_thread = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok"})

        elif self.path == "/screenshot":
            try:
                # Run screenshot capture on main thread
                code = (
                    "from blender_remote.capture import capture_screenshot\n"
                    "__result__ = capture_screenshot()"
                )
                result = executor.execute_on_main_thread(code)
                if result.get("status") == "ok" and "result" in result:
                    self._send_json({"status": "ok", "image": result["result"]})
                else:
                    self._send_json(result, status=500)
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, status=500)

        elif self.path.startswith("/logs"):
            logs = capture.get_logs()
            self._send_json({"status": "ok", "logs": logs})

        else:
            self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        if self.path == "/exec":
            body = self._read_body()
            try:
                data = json.loads(body)
                code = data.get("code", "")
                result = executor.execute_on_main_thread(code)
                self._send_json(result)
            except json.JSONDecodeError:
                self._send_json({"status": "error", "error": "Invalid JSON"}, status=400)
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, status=500)

        else:
            self._send_json({"error": "Not found"}, status=404)


def start(port: int = 9876):
    global _server, _thread
    _server = HTTPServer(("127.0.0.1", port), Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()


def stop():
    global _server, _thread
    if _server:
        _server.shutdown()
        _server = None
        _thread = None

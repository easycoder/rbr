#!/usr/bin/env python3
"""Dev server: static files + proxy to rbrheating.com API endpoints."""

import http.server
import sys
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
REMOTE = "https://rbrheating.com"

# API paths that should be proxied to the remote server
API_PATHS = {"/credentials", "/register", "/verify", "/pair", "/config", "/recover"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def _proxy(self, method):
        if self.path not in API_PATHS:
            return False

        url = REMOTE + self.path
        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None

        try:
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                status = resp.status
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())
        return True

    def do_GET(self):
        if not self._proxy("GET"):
            super().do_GET()

    def do_POST(self):
        if not self._proxy("POST"):
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        print(f"Serving on http://localhost:{PORT}")
        httpd.serve_forever()

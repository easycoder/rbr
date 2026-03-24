#!/usr/bin/env python3
"""Simple HTTP server that serves static files and proxies /credentials."""

import http.server
import sys
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
CREDENTIALS_URL = "https://rbrheating.com/credentials.php"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/credentials":
            try:
                with urllib.request.urlopen(CREDENTIALS_URL) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        print(f"Serving on http://localhost:{PORT}")
        httpd.serve_forever()

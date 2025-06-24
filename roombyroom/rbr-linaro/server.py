from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import urllib.parse

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # Parse query parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        response = f"""
        <html>
            <body>
                <h1>Simple Python HTTP Server</h1>
                <p>GET request received at path: {self.path}</p>
                <p>Query parameters: {query_params}</p>
                <form method="post">
                    <input type="text" name="data" value="Test data">
                    <button type="submit">POST Test</button>
                </form>
            </body>
        </html>
        """
        self.wfile.write(response.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        # Parse POST data
        post_params = urllib.parse.parse_qs(post_data)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        response = f"""
        <html>
            <body>
                <h1>Simple Python HTTP Server</h1>
                <p>POST request received</p>
                <p>POST data: {post_params}</p>
                <a href="/">Back to GET</a>
            </body>
        </html>
        """
        self.wfile.write(response.encode('utf-8'))

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Server running on port {port}")
    httpd.serve_forever()

def start_server_in_background(port=8000):
    server_thread = threading.Thread(target=run_server, args=(port,))
    server_thread.daemon = True  # This makes the thread exit when the main program exits
    server_thread.start()
    return server_thread

if __name__ == '__main__':
    # Start the server in background
    server_thread = start_server_in_background()
    print("Server is running in the background. Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down server...")

"""Deny-by-default HTTP demo proxy. CONNECT and arbitrary destinations are denied."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_CONNECT(self):
        self.send_error(403, 'Destination denied')

    def forward(self):
        parsed = urlsplit(self.path)
        if (parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:8765'
            or parsed.username or parsed.fragment or self.headers.get('Upgrade')):
            return self.send_error(403, 'Destination denied')
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 <= size <= 4096 or self.headers.get('Transfer-Encoding'):
            return self.send_error(413)
        body = self.rfile.read(size) if size else None
        connection = http.client.HTTPConnection('127.0.0.1', 8765, timeout=5)
        try:
            connection.request(self.command, parsed.path + ('?' + parsed.query if parsed.query else ''),
                               body, {'Content-Type': self.headers.get('Content-Type', 'application/octet-stream')})
            response = connection.getresponse()
            payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024:
                return self.send_error(502)
            self.send_response(response.status)
            for name in ('Content-Type', 'Location', 'Content-Security-Policy'):
                if value := response.getheader(name):
                    self.send_header(name, value)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (OSError, http.client.HTTPException):
            self.send_error(502)
        finally:
            connection.close()

    do_GET = forward
    do_POST = forward

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8767), Handler).serve_forever()

"""Synthetic-only CRM. No enterprise accounts, email delivery or external calls."""
import html
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

def serve():
    records = {}
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def page(self, body, status=200):
            payload = ('<!doctype html><html><head><title>AutoQA Synthetic CRM</title></head>'
                       '<body><h1>Synthetic CRM sandbox</h1>' + body + '</body></html>').encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == '/':
                return self.page('<form method="post" action="/customers">'
                    '<label>Customer Name<input aria-label="Customer Name" name="name" required maxlength="200"></label>'
                    '<label>Email<input aria-label="Email" name="email" required maxlength="200"></label>'
                    '<button type="submit">Save</button></form>')
            if self.path.startswith('/records/'):
                with lock:
                    record = records.get(self.path[9:])
                if record:
                    return self.page('<h2>Customer saved</h2><dl><dt>Customer Name</dt><dd data-testid="customer-name">'
                        + html.escape(record['name']) + '</dd><dt>Email</dt><dd data-testid="customer-email">'
                        + html.escape(record['email']) + '</dd></dl>')
            self.page('Not found', 404)

        def do_POST(self):
            if self.path != '/customers':
                return self.page('Not found', 404)
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                return self.page('Invalid request', 400)
            data = parse_qs(self.rfile.read(size).decode())
            if set(data) != {'name', 'email'} or any(len(v) != 1 or len(v[0]) > 200 for v in data.values()):
                return self.page('Invalid fields', 400)
            record_id = uuid.uuid4().hex
            with lock:
                records[record_id] = {k: v[0] for k, v in data.items()}
            self.send_response(303)
            self.send_header('Location', '/records/' + record_id)
            self.send_header('Content-Length', '0')
            self.end_headers()
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()

if __name__ == '__main__':
    serve()

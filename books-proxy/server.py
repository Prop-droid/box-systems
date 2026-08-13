#!/usr/bin/env python3
"""books-proxy: expose Calibre-Web under the /books subpath on the public funnel.

Chain: tailscale funnel :8443 --set-path=/books (strips prefix, public)
       -> this proxy 127.0.0.1:8084 (adds X-Script-Name: /books)
       -> calibre-web 127.0.0.1:8083
Calibre-Web needs X-Script-Name to generate /books/... URLs; tailscale serve
cannot inject headers, hence this shim. Auth stays calibre-web's own.
"""
import http.server
import socketserver
import urllib.request
import urllib.error

UPSTREAM = "http://127.0.0.1:8083"
PREFIX = "/books"
HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailers",
              "proxy-authorization", "proxy-authenticate", "upgrade"}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in HOP_BY_HOP and k.lower() != "host":
                req.add_header(k, v)
        req.add_header("X-Script-Name", PREFIX)
        req.add_header("X-Forwarded-Proto", "https")
        try:
            resp = urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception:
            self.send_error(502)
            return
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() not in HOP_BY_HOP and k.lower() != "content-length":
                self.send_header(k, v)
        data = resp.read()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _proxy

    def log_message(self, fmt, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    Server(("127.0.0.1", 8084), Handler).serve_forever()

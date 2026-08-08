#!/usr/bin/env python3
"""Tiny mock product API for Universal Sidecar connector demos.

Endpoints:
  GET /health
  GET /api/orders/{id}
  GET /api/keprix/v1/health
  POST /api/keprix/v1/events/ack

Run: python3 server.py
Listens on 127.0.0.1:8099
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8099

ORDERS = {
    "ord_1001": {
        "id": "ord_1001",
        "status": "paid",
        "total": 42.50,
        "currency": "GBP",
        "created_at": "2026-08-01T10:00:00Z",
        "items": [{"sku": "SKU-1", "qty": 2}],
    },
    "ord_1002": {
        "id": "ord_1002",
        "status": "pending",
        "total": 19.00,
        "currency": "GBP",
        "created_at": "2026-08-02T12:00:00Z",
        "items": [{"sku": "SKU-2", "qty": 1}],
    },
}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockProject/1.0"

    def _json(self, code: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"status": "ok"})
            return
        if path == "/api/keprix/v1/health":
            self._json(200, {"status": "ok", "product": "mock-project"})
            return
        if path.startswith("/api/orders/"):
            order_id = path.rsplit("/", 1)[-1]
            order = ORDERS.get(order_id)
            if not order:
                self._json(404, {"error": "order not found"})
                return
            self._json(200, order)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/keprix/v1/events/ack":
            payload = self._read_json()
            self._json(200, {"acked": True, "id": payload.get("id")})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[mock-project] {self.address_string()} - {fmt % args}")


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"mock-project listening on http://{HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

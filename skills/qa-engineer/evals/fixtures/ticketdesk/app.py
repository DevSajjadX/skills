"""Tiny fake ticketdesk for QA evals: stdlib only, in-memory, fake data."""
import json, random
from http.server import BaseHTTPRequestHandler, HTTPServer

TICKETS = {"a": [{"id": 1, "title": "Printer jam"}, {"id": 2, "title": "VPN down"}],
           "b": [{"id": 3, "title": "Badge broken"}]}
SESSIONS = {"111111": "a", "222222": "b"}  # fake dev codes


class H(BaseHTTPRequestHandler):
    def team(self):
        return SESSIONS.get(self.headers.get("X-Code", ""))

    def send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        t = self.team()
        if self.path.startswith("/api/dev/sent-sms"):
            return self.send(200, {"body": "code 111111" if "qa-a" in self.path else "code 222222"})
        if self.path == "/api/tickets":
            if not t:
                return self.send(401, {"error": "signed_out"})
            return self.send(200, TICKETS[t][:-1] or [])  # seeded bug: drops the newest ticket
        self.send(404, {"error": "not_found"})

    def do_POST(self):
        if self.headers.get("X-Requested-With") != "ticketdesk-web":
            return self.send(400, {"error": "missing_header"})
        self.send(202, {})


if __name__ == "__main__":
    s = HTTPServer(("127.0.0.1", 0), H)
    print(f"web ready at http://127.0.0.1:{s.server_port}", flush=True)
    s.serve_forever()

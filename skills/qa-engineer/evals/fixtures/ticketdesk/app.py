"""Tiny fake ticketdesk for QA evals: stdlib only, in-memory, fake data."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

TICKETS = {1: ("a", "Printer jam"), 2: ("a", "VPN down"), 3: ("b", "Badge broken")}
CODES = {"qa-a@example.test": ("111111", "a"), "qa-b@example.test": ("222222", "b")}  # fake dev codes


class H(BaseHTTPRequestHandler):
    def team(self):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "sess" and v in ("a", "b"):
                return v
        return None

    def send(self, status, body, cookie=None):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        t = self.team()
        path, _, query = self.path.partition("?")
        if path == "/api/dev/sent-sms":
            code = CODES.get(query.removeprefix("email="), ("", ""))[0]
            return self.send(200, {"body": f"code {code}"})
        if path == "/public/board":  # shared on purpose (ADR-0004)
            return self.send(200, [{"id": i, "title": v[1]} for i, v in TICKETS.items()])
        if path == "/api/tickets":
            if not t:
                return self.send(401, {"error": "signed_out"})
            mine = [{"id": i, "title": v[1]} for i, v in TICKETS.items() if v[0] == t]
            return self.send(200, mine[:-1])  # seeded bug: drops the newest ticket
        if path.startswith("/api/tickets/"):
            if not t:
                return self.send(401, {"error": "signed_out"})
            try:
                owner, title = TICKETS[int(path.rsplit("/", 1)[1])]
            except (KeyError, ValueError):
                return self.send(404, {"error": "not_found"})
            if owner != t:
                return self.send(404, {"error": "not_found"})
            return self.send(200, {"title": title})
        self.send(404, {"error": "not_found"})

    def do_POST(self):
        if self.headers.get("X-Requested-With") != "ticketdesk-web":
            return self.send(400, {"error": "missing_header"})
        data = self.body()
        if self.path == "/api/auth/verify":
            code, team = CODES.get(data.get("email", ""), ("", ""))
            if team and data.get("code") == code:
                return self.send(200, {}, f"sess={team}; Path=/; HttpOnly")
            return self.send(401, {"error": "bad_code"})
        t = self.team()
        if self.path == "/api/tickets":
            if not t:
                return self.send(401, {"error": "signed_out"})
            i = max(TICKETS) + 1
            TICKETS[i] = (t, str(data.get("title", "")))
            return self.send(201, {"id": i})
        self.send(202, {})


if __name__ == "__main__":
    s = HTTPServer(("127.0.0.1", 0), H)
    print(f"web ready at http://127.0.0.1:{s.server_port}", flush=True)
    s.serve_forever()

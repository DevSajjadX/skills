# /// script
# requires-python = ">=3.11"
# ///
"""Sign a QA account in and put its session cookies straight into an agent-browser session.

No cookie value is printed, written to disk or returned to the caller: the values go from the
sign-in response to `agent-browser cookies set ... --httpOnly` as process arguments, so the
agent's transcript only ever sees "signed in". (agent-browser's file import, `cookies set --curl`,
drops the HttpOnly flag, which is why this sets cookies one by one.)
Shortcut, declared debt: the values sit in that child process's argv for its lifetime (milliseconds), readable by
the same OS user; move to a stdin or socket import if agent-browser grows an attribute-keeping one.

The sign-in steps come from the project's recipe (JSON), so one helper fits SMS codes read from a
dev inbox, passwords from env vars, or anything else that is plain HTTP:

  uv run qa_login.py --origin http://localhost:3000 --recipe docs/qa/signin.json \\
      --role company-a --session qa-a

  uv run qa_login.py --origin ... --recipe ... --role company-a --jar web/tmp/qa-<date>/a.jar

  uv run qa_login.py selftest

--jar writes a Netscape cookie file (mode 0600) for `curl -b`, and prints only its path. Put it in the
adapter's ignored evidence folder and delete it at cleanup. --session and --jar may be given together.

Exit codes: 0 ok · 2 bad arguments or recipe · 3 a step got an unexpected status ·
4 sign-in set no cookie · 5 an extract found nothing, or a step marked dev_read answered 401/404 (the sender looks real) · 6 agent-browser failed.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

DEFAULT_OK = range(200, 300)
PLACEHOLDER = re.compile(r"\{(env:)?([A-Za-z_][A-Za-z0-9_]*)\}")


class Fail(Exception):
    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def fill(value, env_vars: dict[str, str]):
    """Replace {name} and {env:NAME} in every string of a JSON value."""
    if isinstance(value, str):
        def sub(m: re.Match) -> str:
            if m.group(1):
                if m.group(2) not in os.environ:
                    raise Fail(f"recipe needs env var {m.group(2)}, which is not set", 2)
                return os.environ[m.group(2)]
            if m.group(2) not in env_vars:
                raise Fail(f"recipe uses {{{m.group(2)}}}, which no var or extract defines", 2)
            return env_vars[m.group(2)]
        return PLACEHOLDER.sub(sub, value)
    if isinstance(value, list):
        return [fill(v, env_vars) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, env_vars) for k, v in value.items()}
    return value


def request(conn_cls, url, step: dict, recipe: dict, jar: dict) -> tuple[int, str, list[str]]:
    headers = {**recipe.get("headers", {}), **step.get("headers", {})}
    body = None
    if "json" in step:
        body = json.dumps(step["json"]).encode()
        headers["Content-Type"] = "application/json"
    if jar:
        headers["Cookie"] = "; ".join(f"{k}={m.value}" for k, m in jar.items())
    conn = conn_cls(url.hostname, url.port, timeout=30)
    try:
        conn.request(step.get("method", "GET"), step["path"], body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8", "replace"), resp.headers.get_all("Set-Cookie") or []
    finally:
        conn.close()


def sign_in(origin: str, recipe: dict, role: str, extra: dict[str, str]) -> list:
    """Run the role's steps against the origin; return the session's cookie morsels."""
    roles = recipe.get("roles", {})
    if role not in roles:
        raise Fail(f"no role {role!r} in the recipe (has: {', '.join(roles) or 'none'})", 2)
    spec = roles[role]
    steps = recipe.get("flows", {}).get(spec.get("flow", ""), spec.get("steps"))
    if not steps:
        raise Fail(f"role {role!r} names no steps or known flow", 2)
    values = {**{k: fill(v, {}) for k, v in spec.get("vars", {}).items()}, **extra}

    url = urlsplit(origin)
    conn_cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    jar: dict[str, object] = {}
    for i, raw in enumerate(steps, 1):
        step = fill(raw, values)
        # An inbox step can run before the message lands, so a step with an extract may ask again,
        # but only while the status is fine and the pattern has not matched yet.
        ok = step.get("ok", DEFAULT_OK)
        for attempt in range(step.get("retries", 5) + 1 if step.get("extract") else 1):
            if attempt:
                time.sleep(step.get("retry_delay", 0.5))
            status, text, set_cookies = request(conn_cls, url, step, recipe, jar)
            if status not in ok or all(re.search(p, text) for p in step.get("extract", {}).values()):
                break
        if step.get("dev_read") and status in (401, 404):
            raise Fail(f"step {i} {step['path'].split('?')[0]} answered HTTP {status}: no dev inbox, the sender looks real; stop", 5)
        if status not in ok:
            # Status only: a body is a sentence for a person and may echo the input.
            raise Fail(f"step {i} {step.get('method', 'GET')} {step['path'].split('?')[0]} answered HTTP {status}", 3)
        for header in set_cookies:
            parsed = SimpleCookie()
            parsed.load(header)
            for name, morsel in parsed.items():
                if morsel["max-age"] == "0" or morsel.value == "":
                    jar.pop(name, None)
                else:
                    jar[name] = morsel
        for name, pattern in step.get("extract", {}).items():
            m = re.search(pattern, text)
            if not m:
                raise Fail(f"step {i}: nothing in the response matched the {name!r} pattern", 5)
            values[name] = m.group(1) if m.groups() else m.group(0)
    if not jar:
        raise Fail("sign-in finished but set no cookie", 4)
    return list(jar.values())


def inject(cookies: list, origin: str, session: str, browser: str, open_first: bool) -> None:
    def run(args: list[str]) -> None:
        done = subprocess.run([browser, "--session", session, *args], capture_output=True, text=True)
        if done.returncode != 0:
            # The arguments hold cookie values, so report the exit code only.
            raise Fail(f"agent-browser {args[0]} failed with exit {done.returncode}", 6)

    if open_first:
        run(["open", origin])
    for m in cookies:
        args = ["cookies", "set", m.key, m.value, "--url", origin, "--path", m["path"] or "/"]
        if m["httponly"]:
            args.append("--httpOnly")
        if m["secure"]:
            args.append("--secure")
        if m["samesite"]:
            args += ["--sameSite", m["samesite"].capitalize()]
        run(args)


def write_jar(cookies: list, origin: str, path: str) -> None:
    """Netscape cookie file for `curl -b`, created 0600; HttpOnly rows carry the #HttpOnly_ prefix."""
    host = urlsplit(origin).hostname or ""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for m in cookies:
            prefix = "#HttpOnly_" if m["httponly"] else ""
            f.write(f"{prefix}{host}\tFALSE\t{m['path'] or '/'}\t{'TRUE' if m['secure'] else 'FALSE'}\t0\t{m.key}\t{m.value}\n")


def main(argv: list[str]) -> int:
    if argv[:1] == ["selftest"]:
        return selftest()
    p = argparse.ArgumentParser(description="Sign a QA role in and load its cookies into an agent-browser session.")
    p.add_argument("--origin", required=True, help="the web origin the browser uses, e.g. http://localhost:3000")
    p.add_argument("--recipe", required=True, help="the project's sign-in recipe (JSON)")
    p.add_argument("--role", required=True, help="a role named in the recipe")
    p.add_argument("--session", help="the agent-browser session to load the cookies into")
    p.add_argument("--jar", help="also (or only) write a 0600 Netscape cookie file here for curl -b; prints the path, never a value")
    p.add_argument("--var", action="append", default=[], metavar="NAME=VALUE", help="override a recipe var")
    p.add_argument("--no-open", action="store_true", help="the session already has the origin open")
    p.add_argument("--agent-browser", default="agent-browser", help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    try:
        recipe = json.load(open(a.recipe, encoding="utf-8"))
        extra = dict(v.split("=", 1) for v in a.var)
        cookies = sign_in(a.origin.rstrip("/"), recipe, a.role, extra)
        if not a.session and not a.jar:
            raise Fail("give --session, --jar or both", 2)
        if a.session:
            inject(cookies, a.origin.rstrip("/"), a.session, a.agent_browser, not a.no_open)
        if a.jar:
            write_jar(cookies, a.origin.rstrip("/"), a.jar)
    except Fail as e:
        print(f"qa_login: {e}", file=sys.stderr)
        return e.code
    except (OSError, ValueError) as e:
        print(f"qa_login: {e}", file=sys.stderr)
        return 2
    where = ", ".join(x for x in (a.session and f"agent-browser session {a.session}", a.jar and f"jar {a.jar}") if x)
    print(f"signed in {a.role} into {where} ({len(cookies)} cookies, values not shown)")
    return 0


def selftest() -> int:
    """A fake origin with an SMS-code sign-in, and a fake agent-browser that records its argv."""
    import tempfile

    class Origin(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, status, body=b"", cookies=()):
            self.send_response(status)
            for c in cookies:
                self.send_header("Set-Cookie", c)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.headers.get("X-Requested-With") != "qa-test":
                return self._send(400)
            if self.path == "/api/start":
                return self._send(200, cookies=["pending=p1; Path=/; HttpOnly; SameSite=Lax"])
            if self.path == "/api/start429":
                return self._send(429, cookies=["pending=p1; Path=/; HttpOnly; SameSite=Lax"])
            if self.path == "/api/verify429":
                return self._send(429, b"a sentence for a person")
            if self.path == "/api/verify":
                if data.get("code") == "123456" and "pending=p1" in (self.headers.get("Cookie") or ""):
                    return self._send(200, cookies=["pending=; Path=/; Max-Age=0", "sess=s3cr3t; Path=/; HttpOnly; SameSite=Strict"])
                return self._send(401)
            self._send(404)

        reads = 0
        real_reads = 0

        def do_GET(self):
            if self.path.startswith("/api/dev/sms"):
                Origin.reads += 1
                # The first read finds an empty inbox, as when the message lands after the start step.
                inbox = [] if Origin.reads == 1 else [{"text": "Your code is 123456"}]
                return self._send(200, json.dumps(inbox).encode())
            if self.path.startswith("/api/dev/real"):
                Origin.real_reads += 1
                return self._send(401)
            self._send(404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    flow = [
        {"method": "POST", "path": "/api/start", "json": {"mobile": "{mobile}"}},
        {"method": "GET", "path": "/api/dev/sms?m={mobile}", "extract": {"code": r"\b(\d{6})\b"}},
        {"method": "POST", "path": "/api/verify", "json": {"mobile": "{mobile}", "code": "{code}"}},
    ]
    recipe = {
        "headers": {"X-Requested-With": "qa-test"},
        "flows": {"sms": flow},
        "roles": {"a": {"flow": "sms", "vars": {"mobile": "09000000001"}}, "env": {"flow": "sms", "vars": {"mobile": "{env:QA_SELFTEST_MOBILE}"}}},
    }
    checks: list[tuple[str, bool]] = []

    cookies = sign_in(origin, recipe, "a", {})
    checks.append(("sign-in keeps only the live session cookie", [m.key for m in cookies] == ["sess"]))
    checks.append(("an empty inbox is read again until the code lands", Origin.reads == 2))
    checks.append(("HttpOnly and SameSite survive parsing", bool(cookies[0]["httponly"]) and cookies[0]["samesite"] == "Strict"))

    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "argv.jsonl")
        fake = os.path.join(d, "fake-agent-browser")
        with open(fake, "w") as f:
            f.write(f"#!{sys.executable}\nimport json,sys\nopen({log!r},'a').write(json.dumps(sys.argv[1:])+'\\n')\n")
        os.chmod(fake, 0o700)
        inject(cookies, origin, "qa-a", fake, True)
        calls = [json.loads(line) for line in open(log)]
    checks.append(("opens the origin, then sets the cookie", calls[0][2:] == ["open", origin] and calls[1][2:5] == ["cookies", "set", "sess"]))
    checks.append(("passes HttpOnly and SameSite to agent-browser", "--httpOnly" in calls[1] and calls[1][calls[1].index("--sameSite") + 1] == "Strict"))

    try:
        sign_in(origin, recipe, "env", {})
        checks.append(("a missing env var stops with exit 2", False))
    except Fail as e:
        checks.append(("a missing env var stops with exit 2", e.code == 2))

    bad = {**recipe, "headers": {}}
    try:
        sign_in(origin, bad, "a", {})
        checks.append(("a refused step stops with exit 3 and no body", False))
    except Fail as e:
        checks.append(("a refused step stops with exit 3 and no body", e.code == 3 and "HTTP 400" in str(e)))

    # A resend wait (429 on the step that sends the code) still signs in with the live code.
    resend = {**recipe, "flows": {"sms": [{**flow[0], "path": "/api/start429", "ok": [200, 429]}, *flow[1:]]}}
    checks.append(("a resend wait (429 in ok) still signs in", [m.key for m in sign_in(origin, resend, "a", {})] == ["sess"]))
    strict = {**recipe, "flows": {"sms": [{**flow[0], "path": "/api/start429"}, *flow[1:]]}}
    try:
        sign_in(origin, strict, "a", {})
        checks.append(("a 429 not listed in ok stops with exit 3", False))
    except Fail as e:
        checks.append(("a 429 not listed in ok stops with exit 3", e.code == 3 and "HTTP 429" in str(e)))

    # A rate-limited verify reports the status only, never the body.
    limited = {**recipe, "flows": {"sms": [*flow[:2], {**flow[2], "path": "/api/verify429"}]}}
    try:
        sign_in(origin, limited, "a", {})
        checks.append(("a rate-limited verify exits 3 with the status only", False))
    except Fail as e:
        checks.append(("a rate-limited verify exits 3 with the status only", e.code == 3 and "HTTP 429" in str(e) and "sentence" not in str(e)))

    # A real sender has no dev inbox: the read answers 401 and the run stops rather than going around it.
    real = {**recipe, "flows": {"sms": [flow[0], {**flow[1], "path": "/api/dev/real", "dev_read": True}, flow[2]]}}
    try:
        sign_in(origin, real, "a", {})
        checks.append(("a real sender (no dev inbox) stops with exit 5", False))
    except Fail as e:
        checks.append(("a real sender (no dev inbox) stops with exit 5", e.code == 5 and "HTTP 401" in str(e) and Origin.real_reads == 1))

    with tempfile.TemporaryDirectory() as d:
        jar_path = os.path.join(d, "a.jar")
        write_jar(cookies, origin, jar_path)
        lines = open(jar_path).read().splitlines()
        mode = os.stat(jar_path).st_mode & 0o777
    checks.append(("--jar writes a 0600 Netscape file with the HttpOnly prefix", mode == 0o600 and lines[1].startswith("#HttpOnly_127.0.0.1\tFALSE\t/\tFALSE\t0\tsess\t")))

    server.shutdown()
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

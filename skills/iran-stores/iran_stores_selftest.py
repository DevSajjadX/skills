"""Core selftest cases for iran_stores.py (`iran_stores.py selftest` imports this). Every value is fake."""

from __future__ import annotations

import contextlib
import io
import json
import struct
import tempfile
import threading
import time
import types
import urllib.error
from pathlib import Path
from unittest import mock

import blazor
import iran_stores as core
from iran_stores import Blocked, LayoutChanged


def patch_fetch(fetch):
    """Patch the network seam with a text stand-in `fetch(req, timeout) -> (status, str body, headers)`."""
    def raw(req, timeout=25):
        code, body, headers = fetch(req, timeout)
        return code, body.encode(), headers
    return mock.patch.object(core, "_fetch_raw", raw)


def outcome(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Blocked as e:
        return f"blocked: {e}"
    except urllib.error.HTTPError as e:
        return f"http {e.code}"


def http(*replies):
    """A _fetch stand-in answering queued (status, body[, headers]); returns (call log, fetch)."""
    calls, queue = [], list(replies)

    def fetch(req, timeout=25):
        calls.append(req.full_url)
        r = queue.pop(0) if len(queue) > 1 else queue[0]
        return r if len(r) == 3 else (*r, {})
    return calls, fetch


def core_cases():
    cases = []
    with mock.patch.object(time, "sleep", lambda s: None):
        for name, replies, want, ncalls in [
            ("core 490 is a block", [(490, "")], "blocked: bot check (HTTP 490)", 1),
            ("core 418 cookie-challenge page is a block, no retry", [(418, "<script>cookie</script>")], "blocked: bot check (HTTP 418)", 1),
            ("core 403 with a challenge page is a block", [(403, "<title>Just a moment...</title>")], "blocked: bot check (HTTP 403)", 1),
            ("core 429 with a captcha body is a block, no retry", [(429, "captcha")], "blocked: bot check (HTTP 429)", 1),
            ("core bare 403 is a plain error", [(403, "<html>forbidden</html>")], "http 403", 1),
            ("core 404 is a plain error", [(404, "")], "http 404", 1),
            ("core 503 retries twice then fails", [(503, "x")], "http 503", 3),
            ("core 429 retries then succeeds", [(429, ""), (200, "ok")], "ok", 2),
        ]:
            calls, fetch = http(*replies)
            with patch_fetch(fetch):
                cases.append((name, (outcome(core.get, "https://example.com/"), len(calls)), (want, ncalls)))
        slept = []
        with mock.patch.object(time, "sleep", slept.append), patch_fetch(http((502, ""))[1]):
            outcome(core.get, "https://example.com/")
        cases.append(("core retry backoff doubles", slept, [0.5, 1.0]))
        cases.append(("core _is_block: 490, challenge 403, plain 403", (core._is_block(490, ""), core._is_block(403, "captcha"), core._is_block(403, "nope")), (True, True, False)))
        for name, body, want in [("core JSON reply parses", '{"a": 1}', {"a": 1}),
                                 ("core HTML where JSON expected is a block", "<html>robot?</html>",
                                  "blocked: a non-JSON reply, taken as its bot check")]:
            with patch_fetch(http((200, body))[1]):
                cases.append((name, outcome(core.get_json, "https://example.com/"), want))
        for name, reply in [("core 204 is an empty result, not a block", (204, "")), ("core empty 200 is an empty result", (200, " \n"))]:
            with patch_fetch(http(reply)[1]):
                cases.append((name, (outcome(core.get_json, "https://example.com/"), outcome(core.post_json, "https://example.com/", {})), ({}, "{}")))
        sent = []
        with patch_fetch(lambda req, timeout=25: (sent.append(req) or (200, "{}", {}))):
            core.post_json("https://example.com/", {"q": 1})
        cases.append(("core post_json sends JSON", (sent[0].data, sent[0].get_header("Content-type")), (b'{"q": 1}', "application/json")))

        with tempfile.TemporaryDirectory() as d, mock.patch.object(core, "CACHE_DIR", Path(d)):
            for store, cooldown in [("alpha", 600), ("beta", 1800)]:
                def call(body, store=store):
                    with patch_fetch(http((200, body))[1]):
                        core.PACING[store] = (0, cooldown)
                        return outcome(core.get_json, "https://example.com/", store=store)
                first = (call('{"r": 1}'), core.state_path(store).read_text().split()[0])
                second = (call("<html>robot?</html>"), core.state_path(store).read_text().split()[0])
                calls, fetch = http((200, "{}"))
                with patch_fetch(fetch):
                    core.PACING[store] = (0, cooldown)
                    third = (outcome(core.get_json, "https://example.com/", store=store), len(calls))
                core.state_path(store).write_text(f"blocked {time.time() - cooldown - 1}")
                fourth = call("{}")
                cases += [
                    (f"paced {store}: success records ok", first, ({"r": 1}, "ok")),
                    (f"paced {store}: a block is recorded", second, ("blocked: a non-JSON reply, taken as its bot check", "blocked")),
                    (f"paced {store}: cooldown skips the network, says how long",
                     (third[0].split(";")[0], third[0].split("for ")[1].split()[0], third[1]),
                     ("blocked: bot check hit 0 s ago", str(cooldown), 0)),
                    (f"paced {store}: runs again after the cooldown", fourth, {}),
                ]
            with patch_fetch(http((204, ""))[1]):
                core.PACING["delta"] = (0, 600)
                empty = (outcome(core.get_json, "https://example.com/", store="delta"), core.state_path("delta").read_text().split()[0])
            cases.append(("paced: a 204 records ok, not a block", empty, ({}, "ok")))
            slow = []
            with mock.patch.object(time, "sleep", slow.append):
                core.state_path("gamma").write_text(f"ok {time.time()}")
                with core.paced("gamma", gap=5):
                    pass
            cases.append(("paced gap sleeps out the remainder", 0 < slow[0] <= 5, True))
            cases.append(("paced stores keep separate state", core.state_path("alpha") != core.state_path("beta"), True))
            cases.append(("paced defaults come from DEFAULT_PACE", core.paced.__wrapped__.__defaults__, core.DEFAULT_PACE))
            cases += mcp_cases()

    cases += [
        ("match_level all, case and digits", core.match_level("mx master ۳s", "Logitech MX Master 3S"), "all"),
        ("match_level arabic letters and ZWNJ", core.match_level("كيبورد بی‌سیم", "کیبورد بی سیم لاجیتک"), "all"),
        ("match_level some", core.match_level("mx master 3s", "Logitech MX Anywhere"), "some"),
        ("match_level none", core.match_level("آسیاب", "Logitech"), "none"),
        ("match_level whole words: شیر is not شیرینی", core.match_level("شیر", "شیرینی خامه ای"), "none"),
        ("match_level whole words: pro is not Product", core.match_level("pro", "Product case"), "none"),
        ("match_level whole words: Latin model with punctuation and case", core.match_level("MX Master 3S", "ماوس MX MASTER 3S"), "all"),
        ("match_level empty query is none", (core.match_level("", "x"), core.match_level("  ", "x")), ("none", "none")),
        ("match_level splits the title on punctuation", core.match_level("master", "mx-master/3s"), "all"),
        ("host_match: exact host and subdomain pass, look-alikes and http fail", [core.host_match(u, "example.com") for u in (
            "https://example.com/a", "https://www.example.com/", "http://example.com/", "https://evil.example/example.com", "https://notexample.com/", "https://example.com.evil.net/")],
         [True, True, False, False, False, False]),
        ("discount_pct: round, no discount, zero base, missing, free", (core.discount_pct(75, 100), core.discount_pct(100, 100), core.discount_pct(5, 0), core.discount_pct(None, 100), core.discount_pct(0, 100)), (25, 0, 0, 0, 100)),
        ("first: group 1 or None, across lines", (core.first(r"a(.)b", "xa\nb"), core.first(r"a(.)b", "a1b"), core.first(r"z(.)", "a")), ("\n", "1", None)),
        ("json_ld: list, @graph and a broken block", [x.get("@type") for x in core.json_ld(
            '<script type="application/ld+json">[{"@type":"A"}]</script><script type="application/ld+json">{"@graph":[{"@type":"B"}]}</script>'
            '<script type="application/ld+json">{oops</script>')], ["A", "B"]),
        ("rial_to_toman takes a string", (core.rial_to_toman("158000"), core.rial_to_toman(0)), (15800, None)),
        ("jalali 30 Esfand in a non-leap year is None", core.jalali_to_iso("1404/12/30"), None),
        ("jalali 29 Esfand in a non-leap year is a date", core.jalali_to_iso("1404/12/29"), "2026-03-20"),
        ("jalali 30 Esfand in a leap year is a date", core.jalali_to_iso("30 اسفند 1403"), "2025-03-20"),
        ("jalali day", core.jalali_to_iso("1405/07/11"), "2026-10-03"),
        ("jalali with month name and persian digits", core.jalali_to_iso("۱۱ مهر ۱۴۰۵"), "2026-10-03"),
        ("jalali leap edge", core.jalali_to_iso("1403/12/30"), "2025-03-20"),
        ("jalali garbage is None", core.jalali_to_iso("امروز"), None),
        ("jalali day 32 is None", core.jalali_to_iso("1405/01/32"), None),
        ("jalali day 31 in month 7 to 12 is None", (core.jalali_to_iso("1405/07/31"), core.jalali_to_iso("1405/12/31")), (None, None)),
        ("jalali day 31 in month 1 to 6 is valid", core.jalali_to_iso("1405/06/31"), "2026-09-22"),
        ("number persian digits", core.number("۱۲,۵۰۰"), 12500),
        ("number takes an int and None", (core.number(12500), core.number(None), core.number(0)), (12500, None, 0)),
        ("rial_to_toman zero is None", core.rial_to_toman(0), None),
        ("dig walks a path", core.dig({"a": {"b": [1]}}, "a", "b", kind=list), [1]),
        ("dig null list is empty", core.dig({"a": None}, "a", kind=list), []),
        ("dig missing key fails loudly", lambda: core.dig({"a": {}}, "a", "b"), LayoutChanged),
        ("dig wrong type fails loudly", lambda: core.dig({"a": 1}, "a", kind=list), LayoutChanged),
        ("asking: real price, token, repeated digit, keyboard run, none", [core.asking(x) for x in (5_000_000, 1_000, 1111111, 1234567, None)],
         [(5_000_000, False), (None, True), (None, True), (None, True), (None, True)]),
        ("with_fair: three priced rows, a tie and a single row", ([r["fair"] for r in core.with_fair([{"toman": 5}, {"toman": 5}, {"toman": 9}])], core.with_fair([{"toman": 5}])[0]["fair"]), ([0.0, 0.0, 1.0], None)),
        *discovery_cases(),
        *installment_cases(),
        *blazor_cases(),
        *raw_cases(),
    ]
    return cases


def discovery_cases():
    good = {"NAME": "shop", "KIND": "general", "DEFAULT": False, "CREDIT": None, "search": lambda *a, **k: []}
    fake = types.SimpleNamespace

    def bad(**over):
        return lambda: core.check_module(fake(**{**good, **over}), {})

    def lacking(key):
        return lambda: core.check_module(fake(**{k: v for k, v in good.items() if k != key}), {})
    return [
        ("discovery: a valid module passes", core.check_module(fake(**{**good, "CREDIT": "x/y (MIT)"}), {}), None),
        ("discovery: a duplicate NAME is rejected", lambda: core.check_module(fake(**good), {"shop": object()}), ValueError),
        ("discovery: a missing KIND is rejected", lacking("KIND"), ValueError),
        ("discovery: a missing search is rejected", lacking("search"), ValueError),
        ("discovery: an unknown KIND is rejected", bad(KIND="toys"), ValueError),
        ("discovery: a non-bool DEFAULT is rejected", bad(DEFAULT="yes"), ValueError),
        ("discovery: an empty NAME is rejected", bad(NAME=""), ValueError),
        ("discovery: a non-string CREDIT is rejected", bad(CREDIT=3), ValueError),
        ("discovery: a non-callable search is rejected", bad(search="x"), ValueError),
        ("discovery: INSTALLMENT_FILTER True passes", core.check_module(fake(**{**good, "INSTALLMENT_FILTER": True}), {}), None),
        ("discovery: a non-bool INSTALLMENT_FILTER is rejected", bad(INSTALLMENT_FILTER="yes"), ValueError),
    ]


def run_cli(mods, *argv):
    """(exit code, stdout lines, stderr text) of main() over fake modules."""
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(core, "_MODULES", mods), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = core.main(["iran_stores.py", *argv])
    return code, out.getvalue().splitlines(), err.getvalue()


def installment_cases():
    ran = []

    def store(name, default, flagged=None, kind="general"):
        def search(q, limit, **kw):
            ran.append((name, kw["installment"]))
            yield core.row(name, q, 1)
        extra = {} if flagged is None else {"INSTALLMENT_FILTER": flagged}
        return types.SimpleNamespace(NAME=name, KIND=kind, DEFAULT=default, CREDIT=None, search=search, **extra)
    mods = {"plain": store("plain", True), "pay": store("pay", False, True), "other": store("other", True, False, "books")}
    results = []
    for argv in (["search", "x", "--installment"], ["search", "x"], ["search", "x", "--store", "plain", "--installment"],
                 ["search", "x", "--store", "pay", "--store", "plain", "--installment"], ["search", "x", "--kind", "books", "--installment"]):
        del ran[:]
        code, out, err = run_cli(mods, *argv)
        results.append((code, [json.loads(x)["store"] for x in out], err, list(ran)))
    skip = lambda n: f"{n}: --installment not available\n"  # noqa: E731
    return [
        ("cli --installment alone runs only the flagged stores", results[0], (0, ["pay"], "", [("pay", True)])),
        ("cli without --installment runs the default stores", results[1], (0, ["plain", "other"], "", [("plain", False), ("other", False)])),
        ("cli --installment with only an unflagged named store: says so, never calls it, exit 3", results[2], (3, [], skip("plain"), [])),
        ("cli --installment with a flagged and an unflagged store: the unflagged is skipped, exit 0", results[3], (0, ["pay"], skip("plain"), [("pay", True)])),
        ("cli --installment with a kind of unflagged stores: exit 3", results[4], (3, [], skip("other"), [])),
        ("cli nearby applies --limit", run_nearby_limit(), 2),
    ]


def run_nearby_limit():
    m = types.SimpleNamespace(NAME="n", nearby=lambda url, city: ({"i": i} for i in range(5)))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        core.run_url_command("nearby", m, types.SimpleNamespace(url="u", city=None, limit=2))
    return len(out.getvalue().splitlines())


def mcp_cases():
    url = "https://mcp.example.com/mcp"
    log = []

    def server(reply_for):
        """A fake MCP endpoint; reply_for(method, params) -> (status, body, kind) with kind json, sse or raw."""
        def fetch(req, timeout=25):
            msg = json.loads(req.data)
            log.append((msg.get("method"), req.get_header("Mcp-session-id")))
            if "id" not in msg:
                return 202, "", {}
            if msg["method"] == "initialize":
                reply = {"jsonrpc": "2.0", "id": msg["id"], "result": {"protocolVersion": core.MCP_PROTOCOL, "capabilities": {}}}
                return 200, json.dumps(reply), {"Mcp-Session-Id": "s-1"}
            status, body, kind = reply_for(msg["method"], msg["params"])
            if kind == "json" and isinstance(body, dict):
                body = json.dumps({"jsonrpc": "2.0", "id": msg["id"], **body})
            elif kind == "sse":
                other = json.dumps({"jsonrpc": "2.0", "id": 99, "result": {}})
                mine = json.dumps({"jsonrpc": "2.0", "id": msg["id"], **body})
                body = f"event: ping\ndata: {other}\n\nevent: message\ndata: {mine}\n\n"
            return status, body, {}
        return fetch

    text = lambda s, e=False: {"result": {"content": [{"type": "text", "text": s}], "isError": e}}  # noqa: E731
    tools = {
        "ok": (200, text("hello"), "json"),
        "json": (200, text('{"a": [1, 2]}'), "json"),
        "sse": (200, text('{"a": 1}'), "sse"),
        "blocked": (490, "", "raw"),
        "html": (200, "<html><body>Checking your browser</body></html>", "raw"),
        "bot": (200, text("HTTP 490: bot check, cooldown 30 minutes", True), "json"),
        "err": (200, text("no such product", True), "json"),
        "rpcerr": (200, {"error": {"code": -32602, "message": "bad args"}}, "json"),
    }
    listing = (200, {"result": {"tools": [{"name": "ok"}]}}, "json")

    def mc(tool, store, at=url):
        del log[:]
        with patch_fetch(server(lambda method, p: tools[p["name"]] if method == "tools/call" else listing)):
            try:
                return core.mcp_call(at, tool, {"q": 1}, store=store)
            except Exception as e:  # noqa: BLE001
                return type(e).__name__, str(e)

    state = lambda store: core.state_path(store).read_text().split()[0]  # noqa: E731
    ok = mc("ok", "m1")
    session_log = list(log)
    js, sse, blocked = mc("json", "m1b"), mc("sse", "m2"), mc("blocked", "m3")
    again, html, bot = mc("ok", "m3"), mc("html", "m4"), mc("bot", "m5")
    err, rpc = mc("err", "m6"), mc("rpcerr", "m7")
    refused = mc("ok", "m9", at="http://mcp.example.com/mcp"), mc("ok", "m9", at="example-mcp@0.0.0")
    with patch_fetch(server(lambda m, p: listing)):
        listed = core.mcp_tools(url, store="m8")
    return [
        ("mcp_call: JSON reply, text result", ok, "hello"),
        ("mcp_call: Mcp-Session-Id from reply 1 is echoed on the later POSTs", session_log,
         [("initialize", None), ("notifications/initialized", "s-1"), ("tools/call", "s-1")]),
        ("mcp_call: JSON in a text block is parsed", js, {"a": [1, 2]}),
        ("mcp_call: an event-stream reply is read from the data line with our id", sse, {"a": 1}),
        ("mcp_call: HTTP 490 is Blocked and recorded", (blocked[0], state("m3")), ("Blocked", "blocked")),
        ("mcp_call: the cooldown then skips the network", again[0], "Blocked"),
        ("mcp_call: an HTML 200 is Blocked and recorded", (html[0], state("m4")), ("Blocked", "blocked")),
        ("mcp_call: isError bot text is Blocked and recorded", (bot[0], state("m5")), ("Blocked", "blocked")),
        ("mcp_call: isError plain error is ValueError with the server text, store stays ok", (err[0], "no such product" in err[1], state("m6")), ("ValueError", True, "ok")),
        ("mcp_call: a JSON-RPC error is ValueError with its message", (rpc[0], "bad args" in rpc[1]), ("ValueError", True)),
        ("mcp_call: a non-https url or a package spec is refused", (refused[0][0], refused[1][0]), ("ValueError", "ValueError")),
        ("mcp_tools: lists the tools", listed, [{"name": "ok"}]),
    ]


# ---------------------------------------------------------------- blazor.py: fake MessagePack frames, batches and circuit

PREPEND, REMOVE, SET_ATTR, REMOVE_ATTR, UPDATE_TEXT, STEP_IN, STEP_OUT, UPDATE_MARKUP, PERM, PERM_END = range(1, 11)
EL, TEXT, ATTR, COMP = 1, 2, 3, 4


def tree(name, attrs, *kids):
    """Frames of one element: ("el", sublen, name), its attrs, then its children (str = text, or another tree())."""
    kids = [[("text", k)] if isinstance(k, str) else k for k in kids]
    at = [("attr", k, v) for k, v in attrs.items()]
    return [("el", 1 + len(at) + sum(len(k) for k in kids), name), *at, *[f for k in kids for f in k]]


def batch(updates, frames):
    """A render batch in the server's binary layout. frames: ("el", sublen, name) | ("text", s) | ("attr", name, value, handler=0)
    | ("comp", sublen, id) | ("raw", frame type). updates: [(component id, [(edit type, sibling index, tree index, name)])]."""
    strings: list[str] = []

    def sidx(x):
        if x is None:
            return -1
        if x not in strings:
            strings.append(x)
        return strings.index(x)
    buf, offs = bytearray(), []
    for cid, edits in updates:
        offs.append(len(buf))
        buf += struct.pack("<ii", cid, len(edits))
        for e in edits:
            typ, sib, tr, name = (list(e) + [0, 0])[:4]
            buf += struct.pack("<iiii", typ, sib, tr, sidx(name) if isinstance(name, str) else -1)
    upd = len(buf)
    buf += struct.pack("<i", len(offs)) + b"".join(struct.pack("<i", o) for o in offs)
    fr = len(buf)
    buf += struct.pack("<i", len(frames))
    for f in frames:
        if f[0] == "el":
            buf += struct.pack("<iiii", EL, f[1], sidx(f[2]), 0) + b"\0" * 4
        elif f[0] == "text":
            buf += struct.pack("<ii", TEXT, sidx(f[1])) + b"\0" * 12
        elif f[0] == "attr":
            buf += struct.pack("<iiiQ", ATTR, sidx(f[1]), sidx(f[2]), f[3] if len(f) > 3 else 0)
        elif f[0] == "markup":
            buf += struct.pack("<ii", 8, sidx(f[1])) + b"\0" * 12
        elif f[0] == "raw":
            buf += struct.pack("<ii", f[1], 0) + b"\0" * 12
        elif f[0] == "comp":
            buf += struct.pack("<iiii", COMP, f[1], f[2], 0) + b"\0" * 4
    dsp = len(buf)
    buf += struct.pack("<i", 0)
    ev = len(buf)
    buf += struct.pack("<i", 0)
    pos, table = len(buf), []
    for x in strings:
        n, head, raw = len(x.encode()), bytearray(), x.encode()
        while True:
            part, n = n & 0x7F, n >> 7
            head.append(part | (0x80 if n else 0))
            if not n:
                break
        table.append(pos)
        buf += bytes(head) + raw
        pos = len(buf)
    st = len(buf)
    buf += b"".join(struct.pack("<i", p) for p in table)
    return bytes(buf + struct.pack("<iiiii", upd, fr, dsp, ev, st))


def search_batch(*cards):
    """One batch that draws search cards (title, publisher, final, list, href) into component 0."""
    div = lambda cls, *k: tree("div", {"class": cls}, *k)  # noqa: E731
    parts = [div("col product-list-item-search-container", div("product-list-item-container", tree(
        "a", {"href": href}, div("product-list-item-name", title), div("product-list-item-producer", pub),
        div("product-list-item-price-final", final), div("product-list-item-price", listed)))) for title, pub, final, listed, href in cards]
    edits, at = [], 0
    for i, part in enumerate(parts):
        edits.append((PREPEND, i, at))
        at += len(part)
    return batch([(0, edits)], [f for part in parts for f in part])


class FakeSite:
    """A fake 30book on the `_fetch_raw` seam: page, negotiate, long poll, hub POSTs; logs (method, path).

    `fail` maps (method, path, n) -> status for the n-th (from 0) such request: 204 answers empty, any other status is a
    challenge page. `js` makes the server send a BeginInvokeJS before the batches; `timeouts` logs each request's timeout."""

    def __init__(self, batches, page=None, status=200, fail=None, js=False):
        self.log, self.out, self.sent, self.batches, self.status = [], [], [], batches, status
        self.fail, self.js, self.seen, self.timeouts = fail or {}, js, {}, []
        self.page = page or ('<!--Blazor:{"type":"server","key":{},"sequence":0,"descriptor":"D"}-->'
                             '<!--Blazor-Server-Component-State:S-->')

    def __call__(self, req, timeout=25):
        path = req.full_url.split("://", 1)[1].split("/", 1)[1].split("?")[0]
        self.log.append((req.get_method(), "/" + path))
        self.timeouts.append(timeout)
        key = (req.get_method(), "/" + path)
        n, self.seen[key] = self.seen.get(key, 0), self.seen.get(key, 0) + 1
        status = self.fail.get((*key, n), self.status)
        if status == 204:
            return 204, b"", {}
        if status != 200:
            return status, b"<title>Just a moment...</title>", {}
        if path == "_blazor/negotiate":
            return 200, json.dumps({"connectionToken": "tok", "connectionId": "id"}).encode(), {}
        if req.get_method() == "GET" and path == "_blazor":
            return (200, self.out.pop(0), {}) if self.out else (200, b"", {})  # a held poll that timed out: 200, empty
        if req.get_method() == "GET":
            return 200, self.page.encode(), {}
        if req.get_method() == "DELETE":
            return 202, b"", {}
        if req.data.endswith(b"\x1e"):
            self.out.append(b"{}\x1e")
            return 200, b"", {}
        for msg in blazor.unframe(req.data):
            self.sent.append(msg)
            if msg[3] == "StartCircuit":
                self.out.append(blazor.frame([3, {}, "0", 3, "circuit-1"]))
            elif msg[3] == "UpdateRootComponents":
                self.out.append(blazor.invocation("JS.AttachComponent", [0, "1"]))
                if self.js:
                    self.out.append(blazor.invocation("JS.BeginInvokeJS", [7, "x.y", "[]", 0, 0]))
                self.out += [blazor.invocation("JS.RenderBatch", [i, b]) for i, b in enumerate(self.batches, 1)]
        return 200, b"", {}


def blazor_cases():
    cases = []
    for v in [None, True, False, 0, 127, 128, 255, 256, 65535, 65536, 2**32 - 1, "", "a" * 31, "a" * 32, "ب" * 200, "x" * 70000, [], [1, ["a", None]], list(range(20)), b"\x00\x01", {}]:
        cases.append((f"blazor messagepack round trip {str(v)[:12]!r}", blazor.mp_decode(blazor.mp_encode(v))[0], v))
    cases += [
        ("blazor messagepack decodes bin16, negative ints, floats and maps", [blazor.mp_decode(b)[0] for b in (b"\xc5\x00\x03abc", b"\xff", b"\xd0\x80", b"\xcb" + struct.pack(">d", 1.5), b"\x82\xa1a\x01\xa1b\xc0")],
         [b"abc", -1, -128, 1.5, {"a": 1, "b": None}]),
        ("blazor messagepack: an unsupported type byte fails", lambda: blazor.mp_decode(b"\xc1"), ValueError),
        ("blazor messagepack: a negative int is not encodable", lambda: blazor.mp_encode(-1), ValueError),
        ("blazor messagepack: a non-empty map is not encodable", lambda: blazor.mp_encode({"a": 1}), TypeError),
        ("blazor messagepack: an unknown type is not encodable", lambda: blazor.mp_encode(1.5), TypeError),
    ]
    msgs = [[1, {}, None, "JS.AttachComponent", [0, "1"]], [3, {}, "0", 3, "circuit-id"], [1, {}, None, "x" * 200, []]]
    cases += [
        ("blazor signalr framing round trip, two-byte length prefix", (blazor.unframe(b"".join(blazor.frame(m) for m in msgs)), len(blazor.frame(msgs[2])) > 128), (msgs, True)),
        ("blazor page markers keep the interactive components and the state blob",
         blazor.page_markers('<!--Blazor:{"type":"server","descriptor":"D0"}--><!--Blazor:{"prerenderId":"a"}--><!--Blazor-Server-Component-State:ST=-->'),
         ([{"type": "server", "descriptor": "D0", "uniqueId": 0}], "ST=")),
    ]

    dom = _dom()
    f = [*tree("div", {"class": "a", "onclick": ""}, tree("span", {}, "hi"), " end"), ("comp", 1, 5), ("text", " after")]
    f[2] = ("attr", "onclick", None, 99)  # an event handler: skipped, never fired
    dom.apply(batch([(0, [(PREPEND, 0, 0), (PREPEND, 1, 6), (PREPEND, 2, 7)])], f))
    div = dom.roots[1].children[0]
    cases.append(("blazor batch: element, attrs without the handler, nested text, component box, sibling text",
                  (div.tag, div.attrs, div.text(), len(dom.roots[1].children), dom.roots[1].text()), ("div", {"class": "a"}, "hi end", 3, "hi end after")))
    dom.apply(batch([(5, [(PREPEND, 0, 0)])], [("text", " child")]))
    dom.apply(batch([(0, [(STEP_IN, 0), (STEP_IN, 0), (UPDATE_TEXT, 0, 0), (STEP_OUT, 0), (REMOVE, 1)])], [("text", "HI")]))
    cases.append(("blazor batch: component content, step in and out, update text, remove", (dom.roots[1].children[0].text(), dom.roots[1].text()), ("HI", "HI child after")))

    d2 = _dom()
    d2.apply(batch([(0, [(PREPEND, i, 4 * i) for i in range(3)])], [f for k in "abc" for f in tree("p", {"id": k, "class": "x"}, k)]))
    d2.apply(batch([(0, [(SET_ATTR, 0, 0), (REMOVE_ATTR, 1, 0, "class")])], [("attr", "id", "z")]))
    attrs = [dict(c.attrs) for c in d2.roots[1].children]
    d2.apply(batch([(0, [(UPDATE_MARKUP, 2, 0)])], [("markup", "<b>M</b>")]))
    d2.apply(batch([(0, [(PERM, 0, 2), (PERM, 2, 0), (PERM_END, 0, 0)])], []))
    cases += [
        ("blazor batch: SET_ATTR and REMOVE_ATTR edit the child at the sibling index", attrs, [{"id": "z", "class": "x"}, {"id": "b"}, {"id": "c", "class": "x"}]),
        ("blazor batch: UPDATE_MARKUP replaces the child with a markup box, PERM swaps keyed children (move-to is the 3rd field)",
         [c.text() for c in d2.roots[1].children], ["M", "b", "a"]),
    ]

    cases += [
        ("blazor batch: an unknown component is a layout change", lambda: blazor.Dom().apply(batch([(3, [(PREPEND, 0, 0)])], [("text", "x")])), LayoutChanged),
        ("blazor batch: an unknown edit type is a layout change", lambda: _dom().apply(batch([(0, [(99, 0, 0)])], [("text", "x")])), LayoutChanged),
        ("blazor batch: an unknown frame type is a layout change", lambda: _dom().apply(batch([(0, [(PREPEND, 0, 0)])], [("raw", 77)])), LayoutChanged),
        ("blazor batch: stepping into text is a layout change", lambda: _dom().apply(batch([(0, [(PREPEND, 0, 0), (STEP_IN, 0)])], [("text", "x")])), LayoutChanged),
    ]

    ready = lambda roots: any(r.find(cls="product-list-item-search-container") for r in roots)  # noqa: E731
    card = ("محصول نمونه", "ناشر", "100 تومان", "120", "/book/0/x")
    good = [batch([(0, [(PREPEND, 0, 0)])], tree("p", {}, "loading")), search_batch(card)]

    def render(site, ready=ready, store="fake30", timeout=5):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(core, "CACHE_DIR", Path(d)), mock.patch.object(core, "_fetch_raw", site):
            core.PACING[store] = (0, 600)
            try:
                return blazor.render(store, "https://www.example.test/search/x", ready, timeout), core.state_path(store).read_text().split()[0]
            except Exception as e:  # noqa: BLE001
                return type(e).__name__, core.state_path(store).read_text().split()[0]
    site = FakeSite(good)
    roots, state = render(site)
    start = next(m for m in site.sent if m[3] == "StartCircuit")
    update = next(m for m in site.sent if m[3] == "UpdateRootComponents")
    ops = json.loads(update[4][0])["operations"]
    cases += [
        ("blazor circuit: negotiate, handshake, StartCircuit with page url and state, both batches acked, closed",
         ([r.find(cls="product-list-item-name").text() for r in roots], state, start[4], ops[0]["ssrComponentId"], [m[4][0] for m in site.sent if m[3] == "OnRenderCompleted"], ("DELETE", "/_blazor") in site.log),
         (["محصول نمونه"], "ok", ["https://www.example.test/", "https://www.example.test/search/x", "[]", "S"], 1, [1, 2], True)),
        ("blazor circuit: no write, every request is a page GET, a poll GET, or a POST or the closing DELETE on /_blazor only",
         (all(m in ("GET", "POST", "DELETE") for m, _ in site.log), all(p.startswith("/_blazor") for m, p in site.log if m != "GET"), site.log[0], sum(m == "DELETE" for m, _ in site.log)),
         (True, True, ("GET", "/search/x"), 1)),
    ]
    def run(site, **kw):
        threads = threading.active_count()
        out = render(site, **kw)
        n = len(site.log)
        time.sleep(0.3)
        return out, sum(m == "DELETE" for m, _ in site.log), len(site.log) == n and threading.active_count() == threads  # poll thread gone
    for name, fail, deletes in [
        ("negotiate", {("POST", "/_blazor/negotiate", 0): 403}, 0),
        ("handshake POST", {("POST", "/_blazor", 0): 403}, 1),
        ("poll", {("GET", "/_blazor", 0): 403}, 1),
        ("later send", {("POST", "/_blazor", 1): 403}, 1),
    ]:
        site = FakeSite(good, fail=fail)
        out, nd, quiet = run(site)
        cases.append((f"blazor circuit: a challenge on the {name} is Blocked and recorded, {deletes} DELETE, no request after return, poll thread gone", (out, nd, quiet), (("Blocked", "blocked"), deletes, True)))
    site = FakeSite(good, fail={("DELETE", "/_blazor", 0): 418})
    cases.append(("blazor circuit: a 418 on the closing DELETE is Blocked and recorded", run(site)[0], ("Blocked", "blocked")))
    site = FakeSite(good, fail={("GET", "/_blazor", 0): 204})
    cases.append(("blazor circuit: SignalR 204 on the poll is a closed circuit, one DELETE", (run(site)[:2]), ((("CircuitError", "ok")), 1)))
    site = FakeSite(good, js=True)
    render(site)
    cases.append(("blazor circuit: a BeginInvokeJS is answered with EndInvokeJSFromDotNet null",
                  [m[4] for m in site.sent if m[3] == "EndInvokeJSFromDotNet"], [[7, True, "[7,true,null]"]]))
    site = FakeSite(good)
    out = run(site, ready=lambda r: False, timeout=2)
    cases.append(("blazor circuit: the timeout is an overall deadline (no request gets more than it) and still sends its DELETE",
                  (out[0], out[1], max(site.timeouts) <= 2), (("CircuitError", "ok"), 1, True)))
    for name, page, want in [("a bot check page", "<title>Just a moment...</title>", ("Blocked", "blocked")), ("a page with no components", "<p>x</p>", ("LayoutChanged", "ok"))]:
        site = FakeSite(good, page=page)
        cases.append((f"blazor render: {name} without Blazor markers is {want[0]} before any circuit", (render(site), site.log), (want, [("GET", "/search/x")])))
    blocked = FakeSite(good, status=403)
    cases.append(("blazor circuit: a challenge on the page GET is Blocked and recorded, nothing else sent", (render(blocked), blocked.log), (("Blocked", "blocked"), [("GET", "/search/x")])))
    garbage = FakeSite([b"\x01\x02"])
    cases.append(("blazor circuit: an unknown batch shape is a layout change", render(garbage)[0], "LayoutChanged"))
    cases.append(("blazor circuit: never ready is a timeout, not a hang", render(FakeSite(good), ready=lambda r: False, timeout=0.6), ("CircuitError", "ok")))
    return cases


def _dom():
    d = blazor.Dom()
    d.attach_root(0, 1)
    return d


def raw_cases():
    seen = []

    def fake(code, body=b"\x00\xff\xfe"):
        return lambda req, timeout=25: (seen.append((req.get_method(), req.data)) or (code, body, {}))

    def run(code, body=b"\x00\xff\xfe", **kw):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(core, "CACHE_DIR", Path(d)), mock.patch.object(core, "_fetch_raw", fake(code, body)):
            core.PACING["rawstore"] = (0, 600)
            try:
                got = core.raw("https://example.com/", store="rawstore", **kw)[:2]
            except Exception as e:  # noqa: BLE001
                got = type(e).__name__
            return got, core.state_path("rawstore").exists() and core.state_path("rawstore").read_text().split()[0]
    cases = [
        ("core raw: bytes come back undecoded, store paced and ok", run(200), ((200, b"\x00\xff\xfe"), "ok")),
        ("core raw: pace=False records nothing", run(200, pace=False), ((200, b"\x00\xff\xfe"), False)),
        ("core raw: a challenge 403 is Blocked and recorded", run(403, b"Just a moment"), ("Blocked", "blocked")),
        ("core raw: a 418 is Blocked even with no body", run(418, b""), ("Blocked", "blocked")),
        ("core raw: a bare 404 is an HTTPError, store stays ok", run(404, b""), ("HTTPError", "ok")),
    ]
    before = len(seen)
    retry = (run(503, b"x"), len(seen) - before)
    cases += [
        ("core raw: no retry on 503, one request", retry, (("HTTPError", "ok"), 1)),
        ("core raw: method and body are passed through", (run(200, method="POST", data=b"x")[0], seen[-1]), ((200, b"\x00\xff\xfe"), ("POST", b"x"))),
    ]
    return cases

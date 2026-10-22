#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["truststore>=0.10"]
# ///
"""Read listings, offers, reviews and seller trust from Iranian stores.

Every price comes out in Toman. Each store lives in `stores/<name>.py`; this file is the
shared core (HTTP, pacing, bot-check handling, helpers) and the CLI.

Usage:
  iran_stores.py search <query> [--store NAME ...] [--kind KIND] [--limit N] [--at LAT,LNG] [--city C] [--installment]
      Without --store/--kind: the DEFAULT stores. --kind runs every store of that kind.
      With --installment and no --store/--kind: only the stores flagged INSTALLMENT_FILTER. A named or kind-selected
      store without the flag prints "<store>: --installment not available" to stderr and is never called; that line
      alone makes the exit code 3 only when no store ran at all (a mixed selection exits 0 if the stores that ran succeed).
  iran_stores.py offers|reviews|questions|history|installments|nearby <product url> [--limit N] [--city C]
      Routed by the URL's store; a store without that command prints "<store>: <command> not available".
  iran_stores.py seller <seller or shop url/id> [--store NAME]
  iran_stores.py stores      # name, kind, default, supported commands
  iran_stores.py selftest    # every module's cases and the core's; exit 1 on any FAIL

Prints one JSON object per line. A store that fails or is blocked prints its reason to stderr,
the other stores still print, and the exit code is 3. After a bot check every run on this
machine skips that store until its cooldown ends; the message says how long. The bot check is
never worked around: open the site in the browser pane instead.

CORE API FOR STORE MODULES (`stores/<name>.py`: `import iran_stores as core`, and call
`core.get(...)` at call time, never `from iran_stores import get`, so tests can patch it)

  Module-level names (see the spec): NAME, KIND, DEFAULT, CREDIT, match(url), search(q, limit, *, at=None, city=None, installment=False),
  optional offers(url), reviews(url, limit), questions(url, limit), history(url), seller(ref),
  installments(url), nearby(url, city), selftest_cases(). Optional INSTALLMENT_FILTER = True (bool) says `search` really
  filters by installment when `installment=True`; a store without it is never called with that flag (the core skips it), so
  its `installment` kwarg is accepted and ignored. Optional PACE = (gap_seconds, cooldown_seconds)
  overrides DEFAULT_PACE for `store=NAME` calls. A module with a bad NAME, KIND, DEFAULT, CREDIT or no callable `search`,
  or a NAME another module already took, fails to load: it lands in LOAD_ERRORS and fails selftest.
  A command function returns an iterable of dicts (or one dict, for seller).

  get(url, headers=None, store=None) -> str
  get_json(url, headers=None, store=None) -> parsed JSON (an HTML reply raises Blocked; an HTTP 204 or
      empty body gives {} and records no block)
  post_json(url, body, headers=None, store=None) -> str (a JSON text; body is a dict, sent as JSON;
      an HTML reply raises Blocked; 204 or an empty body gives "{}")
      `store=NAME` paces the call and records a bot check for that store (paced). Pass it always.
      Raises Blocked on a bot check, urllib.error.HTTPError on any other 4xx/5xx.
  mcp_call(url, tool, args, *, store, timeout=60) -> the tool's result: parsed JSON (dict/list) when its text is JSON,
      else the text. We call only official, site-run MCP servers over streamable HTTP, never third-party local servers
      (no stdio, no spawned packages): `url` must be https, else ValueError. JSON or event-stream replies; Mcp-Session-Id
      kept. Does the initialize handshake each call, inside paced(store) (do not nest it), so gap, cooldown and block file
      apply across runs. A tool result with isError whose text looks like a bot check (490, 418, blocked, bot, captcha,
      challenge, cooldown, robot, ربات) raises Blocked (recorded); any other isError raises ValueError(server text);
      a JSON-RPC error raises ValueError(message); a timeout raises TimeoutError.
  mcp_tools(url, *, store, timeout=60) -> list of tool dicts (tools/list), same rules.
  Tests replace `_fetch_raw(req, timeout=25) -> (status, body bytes, headers)`, the one network seam; `_fetch` is its
  UTF-8 decode, used by get/post_json and MCP.
  raw(url, *, store, method="GET", data=None, headers=None, timeout=25, pace=True) -> (status, body bytes, headers)
      for binary or multi-request exchanges (SignalR): no decoding, no retry, no cookie handling, any method the caller
      needs. A block (`_is_block`) raises Blocked, any other 4xx/5xx urllib.error.HTTPError. pace=True paces the call like
      get(); pace=False is for calls inside `with session(store):` (one paced unit around many requests, so a
      long-poll cannot deadlock the store's lock).
  session(store) -> paced(store, *its PACE): hold it once around a whole exchange, then pass pace=False to raw.
  asking(toman) -> (toman or None, negotiable)   token_price(toman) -> bool   (a price under TOKEN_MAX Toman, one repeated
      digit such as 1111111 or a keyboard run is a seller's "ask me", not an asking price)
  with_fair(rows) -> rows, each with `fair`: the share of the other priced rows that are cheaper (0 cheapest, 1 dearest;
      relative to that one page only; None below two priced rows)
  paced(store, gap, cooldown): context manager (both default to DEFAULT_PACE), one request at a time per store across all
      runs (flock on ~/.cache/iran_stores-<store>). Used by get/post_json: do not nest it.
  row(store, title, toman, seller=None, in_stock=None, url=None, **extra) -> dict
      extras: ad unreliable installment rating rating_count match warranty variant city updated used affiliate
  match_level(q, title) -> "all" | "some" | "none"   (whole query words found among the title's words; Persian-normalised;
      an empty query is "none")
  host_match(url, domain) -> bool   (https and the exact host or a subdomain: the rule for every module's `match`)
  discount_pct(final, base) -> int   (percent off, 0 when there is no discount)
  first(pattern, text) -> first regex group or None     json_ld(doc) -> list of JSON-LD dicts in an HTML page
  TEHRAN = (35.6997, 51.3380)
  rial_to_toman(rial) -> int | None     number(text or int) -> int | None (Persian digits ok)     DIGITS
  dig(data, *path, kind=None) -> value  (LayoutChanged if a key is missing or the type is wrong;
      with kind set, a null value counts as an empty one)
  jalali_to_iso("1405/07/11" or "۱۱ مهر ۱۴۰۵") -> "2026-10-03" | None  (None for 30 Esfand of a non-leap year)
  report(cases) -> fail count. A case is (name, got, want), or (name, fn, ExcType) for a loud failure.
  Blocked, LayoutChanged, UA.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import pkgutil
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.client import responses
from itertools import islice
from pathlib import Path
from urllib.parse import urlparse

import truststore

# Stores import this file as `iran_stores`; when it runs as the script, that must be the same module.
if __name__ == "__main__":
    sys.modules["iran_stores"] = sys.modules["__main__"]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# The OS trust store, as curl and browsers use: Python's bundled roots lack the CA behind emalls.ir.
truststore.inject_into_ssl()

# shortcut: reads undocumented store APIs and page markup, so a store redesign breaks it;
# parsers raise LayoutChanged (exit 3, "check it in the browser") instead of guessing.
# Retire a store's parser when it publishes an official API.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "0123456789" * 2)
BOT_CHECK = re.compile(r"just a moment|captcha|challenge|arvan|attention required|enable javascript", re.I)
RETRY_CODES, MAX_RETRIES, RETRY_BASE, RETRY_CAP = (429, 502, 503, 504), 2, 0.5, 10
DEFAULT_PACE = (0, 600)
TOKEN_MAX = 10_000  # Toman: a "price" below this is the seller's way of saying negotiable
KINDS = ("general", "electronics", "beauty", "fashion", "grocery", "books", "classifieds")
PACING: dict[str, tuple[float, float]] = {}  # store -> (gap, cooldown), filled from modules' PACE
COMMANDS = ("offers", "reviews", "questions", "history", "seller", "installments", "nearby")
CACHE_DIR: Path | None = None  # tests point this at a temp dir


class Blocked(Exception):
    pass


class LayoutChanged(Exception):
    pass


def row(store, title, toman, seller=None, in_stock=None, url=None, **extra):
    return {"store": store, "title": title, "toman": toman, "seller": seller,
            "in_stock": in_stock, "url": url, **extra}


def number(text):
    digits = re.sub(r"\D", "", ("" if text is None else str(text)).translate(DIGITS))
    return int(digits) if digits else None


TEHRAN = (35.6997, 51.3380)


def host_match(url, domain):
    u = urlparse(url)
    return u.scheme == "https" and re.fullmatch(rf"(.+\.)?{re.escape(domain)}", u.hostname or "") is not None


def discount_pct(final, base):
    return round(100 * (base - final) / base) if final is not None and base and base > final else 0


def first(pattern, text):
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else None


def json_ld(doc):
    """Every JSON-LD object in an HTML page (a @graph is flattened); unparsable blocks are skipped."""
    out = []
    for blob in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', doc, re.S):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        for x in data if isinstance(data, list) else [data]:
            if isinstance(x, dict):
                out += x["@graph"] if isinstance(x.get("@graph"), list) else [x]
    return [x for x in out if isinstance(x, dict)]


def rial_to_toman(rial):
    return int(rial) // 10 if rial else None  # a gateway may send Rial as a string


def dig(data, *path, kind=None):
    cur = data
    for i, k in enumerate(path):
        if not isinstance(cur, dict) or k not in cur:
            raise LayoutChanged(f"missing {'.'.join(map(str, path[:i + 1]))}")
        cur = cur[k]
    if kind and cur is None:
        return kind()
    if kind and not isinstance(cur, kind):
        raise LayoutChanged(f"{'.'.join(map(str, path))} is not a {kind.__name__}")
    return cur


_FOLD = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "‌": " ", "‏": "", "‎": ""})


def match_level(q, title):
    """How many query words the title has as whole words: all, some or none (case, ي/ی ك/ک, digits, ZWNJ normalised)."""
    def words(s):
        return re.findall(r"\w+", (s or "").translate(DIGITS).translate(_FOLD).lower())
    t, qs = set(words(title)), words(q)
    hits = sum(w in t for w in qs)
    return "none" if not hits else "all" if hits == len(qs) else "some"


_MONTHS = {"فروردین": 1, "اردیبهشت": 2, "خرداد": 3, "تیر": 4, "مرداد": 5, "شهریور": 6,
           "مهر": 7, "آبان": 8, "آذر": 9, "دی": 10, "بهمن": 11, "اسفند": 12}


def _jalali_date(jy, jm, jd):
    """Arithmetic Jalali to Gregorian (33-year cycle form): days counted from Jan 1 of year gy."""
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33 + 3) // 4) + jd + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    return date(gy, 1, 1) + timedelta(days=days)


def jalali_to_iso(text):
    s = (text or "").translate(DIGITS).strip()
    if m := re.fullmatch(r"(\d{1,2}) (\S+) (\d{4})", s):
        jd, jm, jy = int(m[1]), _MONTHS.get(m[2]), int(m[3])
    elif m := re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", s):
        jy, jm, jd = int(m[1]), int(m[2]), int(m[3])
    else:
        return None
    if not jm or not 1 <= jm <= 12 or not 1 <= jd <= (31 if jm < 7 else 30):
        return None
    # 30 Esfand exists only when the next Farvardin 1 is the day after it (the converter's own leap rule).
    if (jm, jd) == (12, 30) and _jalali_date(jy, 12, 30) + timedelta(days=1) != _jalali_date(jy + 1, 1, 1):
        return None
    return _jalali_date(jy, jm, jd).isoformat()


def token_price(toman):
    """True for a price that is not an asking price: tiny, or one repeated digit (1111111) or a keyboard run."""
    s = str(toman or "")
    return not toman or toman < TOKEN_MAX or (len(s) >= 5 and len(set(s)) == 1) or s in ("123456", "1234567", "12345678", "123456789")


def asking(toman):
    """(toman or None, negotiable)."""
    return (None, True) if token_price(toman) else (toman, False)


def with_fair(rows):
    """Add `fair`: the share of the other priced rows that are cheaper (0 cheapest, 1 dearest), None below two priced rows."""
    prices = [r["toman"] for r in rows if r["toman"]]
    for r in rows:
        r["fair"] = round(sum(p < r["toman"] for p in prices) / (len(prices) - 1), 2) if r["toman"] and len(prices) > 1 else None
    return rows


def state_path(store):
    return (CACHE_DIR or Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")) / f"iran_stores-{store}"


@contextlib.contextmanager
def paced(store, gap=DEFAULT_PACE[0], cooldown=DEFAULT_PACE[1]):
    """Serialise calls to one store across runs; skip the store until `cooldown` ends after a bot check.

    State file: "<ok|blocked> <unix time of the last call>". Raises Blocked at once during a cooldown.
    """
    import fcntl  # POSIX only; imported here so the rest still imports elsewhere

    path = state_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # parallel runs queue up instead of bursting together
        f.seek(0)
        state, _, at = f.read().partition(" ")
        last = float(at or 0)
        if state == "blocked" and time.time() - last < cooldown:
            ago = int(time.time() - last)
            raise Blocked(f"bot check hit {ago} s ago; every run on this machine skips {store} for {int(cooldown) - ago} s more")
        time.sleep(max(0, last + gap - time.time()))
        state = "ok"
        try:
            yield
        except Blocked:
            state = "blocked"
            raise
        finally:
            f.truncate(0)
            f.write(f"{state} {time.time()}")


def _fetch_raw(req, timeout=25):
    """(status, body bytes, headers); the one network seam tests replace."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def _fetch(req, timeout=25):
    """(status, body text, headers): `_fetch_raw` with the body decoded as UTF-8."""
    code, body, headers = _fetch_raw(req, timeout)
    return code, body.decode("utf-8", "replace"), headers


def _is_block(code, body):
    return code in (490, 418) or (code in (403, 429, 503) and bool(BOT_CHECK.search(body[:5000])))


def _check(code, text, url=""):
    """Blocked on a bot check, HTTPError on any other 4xx/5xx; the one place that decides."""
    if _is_block(code, text):
        raise Blocked(f"bot check (HTTP {code})")
    if code >= 400:
        raise urllib.error.HTTPError(url, code, f"{code} {responses.get(code, '')}".strip(), None, None)


def _request(req, expect_json):
    for attempt in range(MAX_RETRIES + 1):
        code, body, _ = _fetch(req)
        if code in RETRY_CODES and attempt < MAX_RETRIES and not _is_block(code, body):
            time.sleep(min(RETRY_BASE * 2 ** attempt, RETRY_CAP))
            continue
        _check(code, body, req.full_url)
        if expect_json and not body.strip():  # 204 or an empty 200 is a store's "nothing here", not a bot check
            return "{}"
        if expect_json and body.lstrip()[:1] not in ("{", "["):
            raise Blocked("a non-JSON reply, taken as its bot check")
        return body


def _call(store, req, expect_json):
    if not store:
        return _request(req, expect_json)
    with session(store):
        return _request(req, expect_json)


def session(store):
    return paced(store, *PACING.get(store, DEFAULT_PACE))


def raw(url, *, store, method="GET", data=None, headers=None, timeout=25, pace=True):
    req = urllib.request.Request(url, data, _headers(headers), method=method)

    def once():  # a Blocked is recorded only inside a paced block: pace=False needs the caller to hold `session`
        code, body, reply = _fetch_raw(req, timeout)
        _check(code, body[:5000].decode("utf-8", "replace"), url)
        return code, body, reply
    if not pace:
        return once()
    with session(store):
        return once()


def _headers(extra):
    return {"User-Agent": UA, "Accept-Language": "fa,en;q=0.8", **(extra or {})}


def get(url, headers=None, store=None):
    return _call(store, urllib.request.Request(url, headers=_headers(headers)), False)


def get_json(url, headers=None, store=None):
    return json.loads(_call(store, urllib.request.Request(url, headers=_headers(headers)), True))


def post_json(url, body, headers=None, store=None):
    req = urllib.request.Request(url, json.dumps(body).encode(), _headers({"Content-Type": "application/json", **(headers or {})}))
    return _call(store, req, True)


MCP_PROTOCOL = "2025-06-18"
MCP_BOT = re.compile(r"\b(490|418)\b|blocked|\bbots?\b|captcha|challenge|cooldown|robot|ربات", re.I)


class _Http:
    """Streamable HTTP: POST JSON-RPC, JSON or text/event-stream replies, optional Mcp-Session-Id."""

    def __init__(self, url, timeout):
        self.url, self.timeout, self.session = url, timeout, None

    def _post(self, msg):
        headers = _headers({"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": MCP_PROTOCOL})
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        try:
            code, body, reply_headers = _fetch(urllib.request.Request(self.url, json.dumps(msg).encode(), headers), self.timeout)
        except TimeoutError:
            raise TimeoutError("MCP server did not answer in time") from None
        _check(code, body, self.url)
        self.session = reply_headers.get("Mcp-Session-Id") or self.session
        return body

    def rpc(self, msg):
        body = self._post(msg)
        if body.lstrip()[:1] in ("{", "["):
            return json.loads(body)
        if "<html" in body[:500].lower():
            raise Blocked("a non-JSON reply, taken as its bot check")
        datas = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")]  # text/event-stream
        replies = [r for r in (json.loads(d) for d in datas if d[:1] == "{") if r.get("id") == msg["id"]]
        if not replies:
            raise ValueError("MCP server sent no JSON-RPC reply")
        return replies[-1]


def _mcp_result(reply, method):
    if not isinstance(reply, dict):
        raise ValueError(f"MCP {method}: not a JSON-RPC reply")
    if reply.get("error"):
        err = reply["error"]
        raise ValueError(f"MCP {method}: {err.get('message') if isinstance(err, dict) else err}")
    return reply.get("result") or {}


def _mcp_session(url, store, timeout, method, params, check=lambda result: result):
    """initialize, one request, `check(result)`; all inside paced(store) so a Blocked from `check` is recorded."""
    if not url.startswith("https://"):
        raise ValueError(f"MCP url must be https: {url}")
    with session(store):
        t = _Http(url, timeout)
        _mcp_result(t.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": MCP_PROTOCOL, "capabilities": {}, "clientInfo": {"name": "iran_stores", "version": "1"}}}), "initialize")
        t._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return check(_mcp_result(t.rpc({"jsonrpc": "2.0", "id": 2, "method": method, "params": params}), method))


def mcp_call(url, tool, args, *, store, timeout=60):
    def check(result):
        text = "".join(c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict) and c.get("type") == "text")
        if result.get("isError"):
            if MCP_BOT.search(text):
                raise Blocked(f"bot check from {tool}: {text[:200]}")
            raise ValueError(text or f"MCP {tool} failed")
        if not text and "structuredContent" in result:
            return result["structuredContent"]
        try:
            return json.loads(text)
        except ValueError:
            return text
    return _mcp_session(url, store, timeout, "tools/call", {"name": tool, "arguments": args}, check)


def mcp_tools(url, *, store, timeout=60):
    return _mcp_session(url, store, timeout, "tools/list", {}).get("tools") or []


def check_module(m, taken):
    """Raise ValueError unless `m` meets the module contract and its NAME is free."""
    for attr, ok in (("NAME", lambda v: isinstance(v, str) and re.fullmatch(r"[a-z0-9_]+", v)), ("KIND", lambda v: v in KINDS),
                     ("DEFAULT", lambda v: isinstance(v, bool)), ("CREDIT", lambda v: v is None or isinstance(v, str) and v)):
        if not hasattr(m, attr) or not ok(getattr(m, attr)):
            raise ValueError(f"{attr} is missing or invalid: {getattr(m, attr, None)!r}")
    if hasattr(m, "INSTALLMENT_FILTER") and not isinstance(m.INSTALLMENT_FILTER, bool):
        raise ValueError(f"INSTALLMENT_FILTER must be a bool: {m.INSTALLMENT_FILTER!r}")
    if not callable(getattr(m, "search", None)):
        raise ValueError("search is missing or not callable")
    if m.NAME in taken:
        raise ValueError(f"NAME {m.NAME!r} is already taken")


def modules():
    """{NAME: module} for every stores/*.py; import failures go to LOAD_ERRORS and stderr."""
    if _MODULES:
        return _MODULES
    pkg = importlib.import_module("stores")
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda i: i.name):
        try:
            m = importlib.import_module(f"stores.{info.name}")
            check_module(m, _MODULES)
            _MODULES[m.NAME] = m
            if getattr(m, "PACE", None):
                PACING[m.NAME] = m.PACE
        except Exception as e:  # noqa: BLE001 one broken module must not hide the others
            LOAD_ERRORS[info.name] = f"{type(e).__name__}: {e}"
            print(f"stores/{info.name}: import failed: {LOAD_ERRORS[info.name]}", file=sys.stderr)
    return _MODULES


_MODULES: dict = {}
LOAD_ERRORS: dict = {}


def supported(m):
    return ["search"] + [c for c in COMMANDS if hasattr(m, c)]


def route(url):
    return next((m for m in modules().values() if hasattr(m, "match") and m.match(url)), None)


def emit(store, make):
    """Print each result as a JSON line; `make` is a thunk so a failed fetch lands in this handler."""
    try:
        res = make()
        n = 0
        for r in [res] if isinstance(res, dict) else res:
            print(json.dumps(r, ensure_ascii=False))
            n += 1
        if not n:
            print(f"{store}: no results", file=sys.stderr)
        return 0
    except Blocked as e:
        print(f"{store}: blocked: {e}; open it in the browser pane, one query at a time", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 one store failing must not hide the others
        print(f"{store}: failed: {type(e).__name__}: {e}; check it in the browser", file=sys.stderr)
    return 3


def report(cases) -> int:
    fails = 0
    for name, got, want in cases:
        if isinstance(want, type) and issubclass(want, BaseException) and callable(got):
            try:
                got()
                ok, detail = False, "\n  want it to raise " + want.__name__
            except want:
                ok, detail = True, ""
            except Exception as e:  # noqa: BLE001
                ok, detail = False, f"\n  want {want.__name__}, got {type(e).__name__}: {e}"
        else:
            ok, detail = got == want, f"\n  want {want!r}\n  got  {got!r}"
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else detail))
    return fails


def selftest() -> int:
    import iran_stores_selftest

    fails = report(iran_stores_selftest.core_cases())
    for name, m in sorted(modules().items()):
        if hasattr(m, "selftest_cases"):
            try:
                fails += report(m.selftest_cases())
            except Exception as e:  # noqa: BLE001 a module whose cases cannot even be built is a failure
                print(f"FAIL  {name}: selftest_cases raised {type(e).__name__}: {e}")
                fails += 1
        else:
            print(f"FAIL  {name}: no selftest_cases")
            fails += 1
    fails += len(LOAD_ERRORS)
    for name, err in LOAD_ERRORS.items():
        print(f"FAIL  stores/{name} failed to import: {err}")
    return 1 if fails else 0


def table():
    print(f"{'name':<16}{'kind':<13}{'default':<9}commands")
    for name, m in sorted(modules().items()):
        print(f"{name:<16}{m.KIND:<13}{'yes' if m.DEFAULT else 'no':<9}{' '.join(supported(m))}")
    return 0


def flagged(m):
    return getattr(m, "INSTALLMENT_FILTER", False)


def run_url_command(cmd, m, a):
    fn = getattr(m, cmd, None)
    if fn is None:
        print(f"{m.NAME}: {cmd} not available", file=sys.stderr)
        return 3
    limit = getattr(a, "limit", None)
    args = (a.url, limit or 10) if cmd in ("reviews", "questions") else (a.url, a.city) if cmd == "nearby" else (a.url,)
    if cmd in ("offers", "history", "installments", "nearby") and limit:
        return emit(m.NAME, lambda: islice(fn(*args), limit))
    return emit(m.NAME, lambda: fn(*args))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("CORE API")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query", nargs="+")
    s.add_argument("--store", action="append")
    s.add_argument("--kind")
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--at", help="LAT,LNG for stores that search by location")
    s.add_argument("--city")
    s.add_argument("--installment", action="store_true", help="only products sold in installments")
    for c in ("offers", "reviews", "questions", "history", "installments", "nearby"):
        u = sub.add_parser(c)
        u.add_argument("url")
        u.add_argument("--limit", type=int)
        u.add_argument("--city")
    sl = sub.add_parser("seller")
    sl.add_argument("url", metavar="seller")
    sl.add_argument("--store")
    sub.add_parser("stores")
    sub.add_parser("selftest")
    a = p.parse_args(argv[1:])
    if a.cmd == "selftest":
        return selftest()
    mods = modules()
    if a.cmd == "stores":
        return table()
    if a.cmd == "search":
        for n in a.store or []:
            if n not in mods:
                p.error(f"unknown store {n!r}; known: {', '.join(sorted(mods))}")
        names = list(a.store or []) + [n for n, m in mods.items() if a.kind and m.KIND == a.kind and n not in (a.store or [])]
        if not names:
            if a.kind:
                p.error(f"no store of kind {a.kind!r}")
            names = [n for n, m in mods.items() if (flagged(m) if a.installment else m.DEFAULT)]
        for n in [n for n in names if a.installment and not flagged(mods[n])]:
            print(f"{n}: --installment not available", file=sys.stderr)
        if a.installment:
            names = [n for n in names if flagged(mods[n])]
            if not names:
                return 3
        try:
            at = tuple(float(x) for x in a.at.split(",")) if a.at else None
            if at and len(at) != 2:
                raise ValueError
        except ValueError:
            p.error("--at takes LAT,LNG")
        q = " ".join(a.query)
        return max(emit(n, lambda m=mods[n]: m.search(q, a.limit, at=at, city=a.city, installment=a.installment)) for n in names)
    if a.cmd == "seller" and a.store:
        if a.store not in mods:
            p.error(f"unknown store {a.store!r}; known: {', '.join(sorted(mods))}")
        m = mods[a.store]
    else:
        m = route(a.url)
        if not m:
            p.error(f"no store matches {a.url!r}" + (" (pass --store NAME for a bare seller id)" if a.cmd == "seller" else ""))
    return run_url_command(a.cmd, m, a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

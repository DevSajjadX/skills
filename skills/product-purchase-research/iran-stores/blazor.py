"""A read-only Blazor Server client on the standard library, for sites whose list pages are drawn by a circuit.

30book's search and listing pages are empty shells: the browser opens a SignalR connection (`/_blazor`, MessagePack
"blazorpack") and applies the binary render batches it receives. This module does the same over SignalR long polling
and builds the result into a small DOM (`Node`). Not a store module (no NAME), so it lives beside iran_stores.py.

Flow: GET the page (component markers and a state blob) -> POST negotiate -> a poll thread GETs `/_blazor?id=` while the
main thread POSTs -> handshake -> StartCircuit -> UpdateRootComponents -> render batches, each acked with
OnRenderCompleted -> stop when the caller's `ready` test passes -> DELETE the connection (SignalR's own close).

All HTTP goes through `core.raw` inside one `core.session(store)`: the whole circuit is one paced unit, a bot check
raises Blocked and is recorded, and nothing retries after it. Only the page GET, the SignalR POSTs and the close DELETE
are ever sent: no click or input event, so nothing on the site is changed. Cookies the site sets are echoed back,
nothing more (no challenge solving, no TLS impersonation, no proxy).

  render(store, url, ready, timeout=20) -> list[Node]   the circuit's root component trees once `ready(roots)` holds
  parse_html(html) -> Node     Node.find / find_all / text() / get() / classes()
  mp_encode / mp_decode / frame / unframe   the MessagePack and SignalR framing
  Dom.apply(batch bytes)   an unknown batch shape raises core.LayoutChanged; a failed circuit raises CircuitError

shortcut: reimplements the undocumented blazorpack / render-batch wire format. Ceiling: a .NET/Blazor upgrade on 30book
turns every search into LayoutChanged. Retire when 30book offers an API or server-rendered search.
"""

from __future__ import annotations

import json
import queue
import re
import struct
import threading
import time
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse

import iran_stores as core

TIMEOUT = 20  # seconds for a whole render: page GET, circuit and close

# ---------------------------------------------------------------- DOM

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCKY = ("br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr")


class Node:
    """An element, or a logical Blazor container (`#c`, a component or markup box). Children are Node or str."""

    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children, self.parent = tag, attrs if attrs is not None else {}, [], None

    def add(self, child, index=None):
        if isinstance(child, Node):
            child.parent = self
        if index is None or index >= len(self.children):
            self.children.append(child)
        else:
            self.children.insert(max(index, 0), child)

    def classes(self):
        return set(self.attrs.get("class", "").split())

    def get(self, name, default=""):
        return self.attrs.get(name) or default

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()

    def find_all(self, tag=None, cls=None):
        return [n for n in self.iter() if (tag is None or n.tag == tag) and (cls is None or cls in n.classes())]

    def find(self, tag=None, cls=None):
        return next(iter(self.find_all(tag, cls)), None)

    def text(self):
        out = []
        self._text(out)
        return " ".join("".join(out).split())

    def _text(self, out):
        if self.tag in ("script", "style"):
            return
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            else:
                if c.tag in BLOCKY:
                    out.append(" ")
                c._text(out)


class _Builder(HTMLParser):
    def __init__(self, root):
        super().__init__(convert_charrefs=True)
        self.stack = [root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: v if v is not None else "" for k, v in attrs})
        self.stack[-1].add(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].add(Node(tag, {k: v if v is not None else "" for k, v in attrs}))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].add(data)


def parse_html(html, root=None):
    """An HTML document or fragment as a tree; comments and the doctype are dropped."""
    root = root or Node("#root")
    b = _Builder(root)
    b.feed(html)
    b.close()
    return root


# ---------------------------------------------------------------- MessagePack (the subset SignalR uses)

_FIXED = {0xCC: ">B", 0xCD: ">H", 0xCE: ">I", 0xCF: ">Q", 0xD0: ">b", 0xD1: ">h", 0xD2: ">i", 0xD3: ">q", 0xCA: ">f", 0xCB: ">d"}
_SIZED = {0xC4: ">B", 0xD9: ">B", 0xC5: ">H", 0xDA: ">H", 0xC6: ">I", 0xDB: ">I"}


def mp_encode(v):
    """None, bool, int 0..2**32-1, str, bytes, list/tuple and the empty map: what the client ever sends."""
    if v is None:
        return b"\xc0"
    if isinstance(v, bool):
        return b"\xc3" if v else b"\xc2"
    if isinstance(v, int):
        for limit, head, fmt in ((128, b"", None), (256, b"\xcc", ">B"), (65536, b"\xcd", ">H"), (2**32, b"\xce", ">I")):
            if 0 <= v < limit:
                return bytes([v]) if fmt is None else head + struct.pack(fmt, v)
        raise ValueError(v)
    if isinstance(v, bytes):
        return b"\xc6" + struct.pack(">I", len(v)) + v
    if isinstance(v, str):
        b = v.encode()
        n = len(b)
        if n < 32:
            return bytes([0xA0 | n]) + b
        if n < 256:
            return b"\xd9" + bytes([n]) + b
        if n < 65536:
            return b"\xda" + struct.pack(">H", n) + b
        return b"\xdb" + struct.pack(">I", n) + b
    if isinstance(v, (list, tuple)):
        n = len(v)
        return (bytes([0x90 | n]) if n < 16 else b"\xdc" + struct.pack(">H", n)) + b"".join(mp_encode(x) for x in v)
    if v == {}:
        return b"\x80"
    raise TypeError(type(v))


def mp_decode(b, i=0):
    """(value, next index). bin gives bytes; an unsupported type byte raises ValueError."""
    t = b[i]
    i += 1
    if t < 0x80:
        return t, i
    if t >= 0xE0:
        return t - 256, i
    if 0x80 <= t <= 0x8F:
        return _mp_seq(b, i, t & 0x0F, True)
    if 0x90 <= t <= 0x9F:
        return _mp_seq(b, i, t & 0x0F, False)
    if 0xA0 <= t <= 0xBF:
        n = t & 0x1F
        return b[i:i + n].decode(), i + n
    if t in _FIXED:
        return struct.unpack_from(_FIXED[t], b, i)[0], i + struct.calcsize(_FIXED[t])
    if t == 0xC0:
        return None, i
    if t in (0xC2, 0xC3):
        return t == 0xC3, i
    if t in _SIZED:
        (n,) = struct.unpack_from(_SIZED[t], b, i)
        i += struct.calcsize(_SIZED[t])
        raw = b[i:i + n]
        return (raw if t in (0xC4, 0xC5, 0xC6) else raw.decode()), i + n
    if t in (0xDC, 0xDD, 0xDE, 0xDF):
        fmt = ">H" if t in (0xDC, 0xDE) else ">I"
        (n,) = struct.unpack_from(fmt, b, i)
        return _mp_seq(b, i + struct.calcsize(fmt), n, t in (0xDE, 0xDF))
    raise ValueError(f"unsupported MessagePack type 0x{t:02x}")


def _mp_seq(b, i, n, as_map):
    out = {} if as_map else []
    for _ in range(n):
        v, i = mp_decode(b, i)
        if as_map:
            k = v
            v, i = mp_decode(b, i)
            out[k] = v
        else:
            out.append(v)
    return out, i


def frame(msg):
    """One hub message: a 7-bit varint length, then the MessagePack array."""
    body = mp_encode(msg)
    n, head = len(body), bytearray()
    while True:
        part, n = n & 0x7F, n >> 7
        head.append(part | (0x80 if n else 0))
        if not n:
            return bytes(head) + body


def unframe(data):
    out, i = [], 0
    while i < len(data):
        n, shift = 0, 0
        while True:
            c = data[i]
            i += 1
            n |= (c & 0x7F) << shift
            shift += 7
            if c < 0x80:
                break
        out.append(mp_decode(data[i:i + n])[0])
        i += n
    return out


def invocation(target, args, invocation_id=None):
    return frame([1, {}, invocation_id, target, args])


HANDSHAKE = b'{"protocol":"blazorpack","version":1}\x1e'

# ---------------------------------------------------------------- render batches

_PREPEND, _REMOVE, _SET_ATTR, _REMOVE_ATTR, _UPDATE_TEXT, _STEP_IN, _STEP_OUT, _UPDATE_MARKUP, _PERM, _PERM_END = range(1, 11)
_ELEMENT, _TEXT, _ATTRIBUTE, _COMPONENT, _REGION, _REF_CAPTURE, _MARKUP, _NAMED_EVENT = 1, 2, 3, 4, 5, 6, 8, 10


class Batch:
    """A binary render batch (layout read off blazor.web.js; the reference client uses the same).

    The last 20 bytes are five int32 offsets: updated components, reference frames, disposed component ids, disposed
    event handler ids, string table. Arrays are `int32 count` + items; a component diff is `componentId`, an edit count
    and 16-byte edits (type, siblingIndex, newTreeIndex or moveTo, removed attribute name index); a frame is 20 bytes.
    """

    def __init__(self, data):
        self.d = data
        n = len(data)
        self.upd, self.frames, self.disp, _, self.strings = (self.i32(n - 20 + 4 * k) for k in range(5))

    def i32(self, at):
        return struct.unpack_from("<i", self.d, at)[0]

    def string(self, idx):
        if idx == -1:
            return None
        off = self.i32(self.strings + 4 * idx)
        n, shift = 0, 0
        while True:
            c = self.d[off]
            off += 1
            n |= (c & 0x7F) << shift
            shift += 7
            if c < 0x80:
                break
        return self.d[off:off + n].decode("utf-8")

    def updated(self):
        for k in range(self.i32(self.upd)):
            at = self.i32(self.upd + 4 + 4 * k)
            cid, cnt = self.i32(at), self.i32(at + 4)
            yield cid, [tuple(self.i32(at + 8 + 16 * j + 4 * f) for f in range(4)) for j in range(cnt)]

    def disposed(self):
        return [self.i32(self.disp + 4 + 4 * k) for k in range(self.i32(self.disp))]

    def frame_at(self, i):
        return self.frames + 4 + 20 * i

    def ftype(self, i):
        return self.i32(self.frame_at(i))

    def sublen(self, i):
        return self.i32(self.frame_at(i) + 4)

    def fstr(self, i, offset):
        return self.string(self.i32(self.frame_at(i) + offset))


def _bad(msg):
    raise core.LayoutChanged(f"30book render batch: {msg}")


class Dom:
    """Component id -> logical container node; applies batches the way blazor.web.js does."""

    def __init__(self):
        self.components, self.roots = {}, {}  # roots: ssrComponentId -> container

    def attach_root(self, component_id, ssr_id):
        self.components[component_id] = self.roots[ssr_id] = Node("#c")

    def apply(self, data):
        b = Batch(data)
        for cid, edits in b.updated():
            if cid not in self.components:
                _bad(f"updates unknown component {cid}")
            self._edits(b, self.components[cid], edits)
        for cid in b.disposed():
            self.components.pop(cid, None)

    def _edits(self, b, parent, edits):
        perm = []
        for typ, sib, tree, extra in edits:
            if typ == _PREPEND:
                self._insert(b, parent, sib, tree)
            elif typ == _REMOVE:
                del parent.children[sib]
            elif typ == _SET_ATTR:
                if isinstance(el := parent.children[sib], Node):
                    self._attr(b, el, tree)
            elif typ == _REMOVE_ATTR:
                if isinstance(el := parent.children[sib], Node):
                    el.attrs.pop(b.string(extra) or "", None)
            elif typ == _UPDATE_TEXT:
                parent.children[sib] = b.fstr(tree, 4) or ""
            elif typ == _UPDATE_MARKUP:
                del parent.children[sib]
                self._markup(b, parent, sib, tree)
            elif typ == _STEP_IN:
                if not isinstance(node := parent.children[sib], Node):
                    _bad("steps into a text node")
                parent = node
            elif typ == _STEP_OUT:
                if parent.parent is None:
                    _bad("steps out of the root")
                parent = parent.parent
            elif typ == _PERM:
                perm.append((sib, tree))
            elif typ == _PERM_END:
                moved = [(parent.children[f], t) for f, t in perm]
                for f, _ in sorted(perm, reverse=True):
                    del parent.children[f]
                for child, t in sorted(moved, key=lambda m: m[1]):
                    parent.add(child, t)
                perm = []
            else:
                _bad(f"unknown edit type {typ}")

    def _insert(self, b, parent, idx, fi):
        t = b.ftype(fi)
        if t == _ELEMENT:
            el = Node(b.fstr(fi, 8) or "div")
            end, j = fi + b.sublen(fi), fi + 1
            while j < end and b.ftype(j) == _ATTRIBUTE:
                self._attr(b, el, j)
                j += 1
            parent.add(el, idx)
            self._range(b, el, 0, j, end)
            return 1
        if t == _TEXT:
            parent.add(b.fstr(fi, 4) or "", idx)
            return 1
        if t == _COMPONENT:
            node = Node("#c")
            self.components[b.i32(b.frame_at(fi) + 8)] = node
            parent.add(node, idx)
            return 1
        if t == _REGION:
            return self._range(b, parent, idx, fi + 1, fi + b.sublen(fi))
        if t == _MARKUP:
            return self._markup(b, parent, idx, fi)
        if t in (_REF_CAPTURE, _NAMED_EVENT):
            return 0
        _bad(f"unknown frame type {t}")

    def _range(self, b, parent, idx, start, end):
        first, j = idx, start
        while j < end:
            idx += self._insert(b, parent, idx, j)
            j += 1 + (b.sublen(j) - 1 if b.ftype(j) in (_ELEMENT, _COMPONENT, _REGION) else 0)
        return idx - first

    def _markup(self, b, parent, idx, fi):
        """A markup frame is ONE logical child (the browser wraps its nodes in a container), whatever it holds."""
        box = Node("#c")
        parse_html(b.fstr(fi, 4) or "", box)
        parent.add(box, idx)
        return 1

    def _attr(self, b, el, fi):
        if struct.unpack_from("<Q", b.d, b.frame_at(fi) + 12)[0]:  # an event handler: this client never fires one
            return
        name, value = b.fstr(fi, 4) or "", b.fstr(fi, 8)
        if value is None:
            el.attrs.pop(name, None)
        else:
            el.attrs[name] = value


# ---------------------------------------------------------------- the circuit


class CircuitError(Exception):
    """The circuit failed (refused, closed early, timed out); the message says where."""


def page_markers(html):
    """The interactive component markers (`<!--Blazor:{...}-->`, type=server) and the persisted-state blob."""
    markers = []
    for m in re.finditer(r"<!--Blazor:(\{.*?\})-->", html):
        d = json.loads(m.group(1))
        if d.get("type") == "server":
            d["uniqueId"] = len(markers)
            markers.append(d)
    s = re.search(r"<!--Blazor-Server-Component-State:(.*?)-->", html)
    return markers, s.group(1) if s else ""


class Circuit:
    """One circuit for one page. `with Circuit(...) as c: roots = c.wait(ready)`; every request is paced by the caller."""

    def __init__(self, store, base, page_url, html, jar=None, deadline=None):
        self.store, self.base, self.url, self.jar = store, base, page_url, jar if jar is not None else {}
        self.deadline, self._jar_lock = deadline or time.monotonic() + TIMEOUT, threading.Lock()
        self.markers, self.state = page_markers(html)
        self.dom, self.token, self.batches, self.last_batch = Dom(), "", 0, 0.0
        self.handshaking = True
        self._inbox, self._stop, self._poller = queue.Queue(), threading.Event(), None

    def _req(self, method, path, params, data=None, content_type="application/octet-stream", timeout=30):
        """(status, body); `timeout` is the per-call cap, cut to what is left of the overall deadline (at least 1 s)."""
        headers = {"Accept": "*/*", "Origin": self.base, "Referer": self.base + "/"}
        if data is not None:
            headers["Content-Type"] = content_type
        with self._jar_lock:  # the poll thread and the main thread both read and write the jar
            if self.jar:
                headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.jar.items())
        code, body, reply = core.raw(f"{self.base}{path}?{urlencode(params)}", store=self.store, method=method, data=data,
                                     headers=headers, timeout=max(1, min(timeout, self.deadline - time.monotonic())), pace=False)
        with self._jar_lock:
            take_cookies(self.jar, reply)
        return code, body

    def _poll(self):
        try:
            while not self._stop.is_set():
                code, body = self._req("GET", "/_blazor", {"id": self.token}, timeout=100)
                if code == 204:  # SignalR long polling: 204 means the server ended the connection
                    if not self._stop.is_set():
                        self._inbox.put(CircuitError("closed: 30book ended the poll (HTTP 204)"))
                    return
                if body:
                    self._inbox.put(body)
                else:
                    time.sleep(0.01)  # a real server holds the poll open; this only paces a reply with no data
        except core.Blocked as e:
            self._inbox.put(e)
        except Exception as e:  # noqa: BLE001 handed to the main thread
            if not self._stop.is_set():
                self._inbox.put(CircuitError(f"poll failed: {type(e).__name__}: {e}"))

    def _send(self, data):
        self._req("POST", "/_blazor", {"id": self.token}, data)

    def __enter__(self):
        _, body = self._req("POST", "/_blazor/negotiate", {"negotiateVersion": 1}, b"", "text/plain;charset=UTF-8")
        try:
            neg = json.loads(body)
        except ValueError:
            raise core.Blocked("a non-JSON negotiate reply, taken as its bot check") from None
        if not isinstance(neg, dict) or not (neg.get("connectionToken") or neg.get("connectionId")):
            raise core.LayoutChanged("30book negotiate reply has no connection token")
        self.token = neg.get("connectionToken") or neg["connectionId"]
        try:
            self._poller = threading.Thread(target=self._poll, daemon=True)
            self._poller.start()
            self._send(HANDSHAKE)
        except BaseException:  # `with` never calls __exit__ when __enter__ raises: stop the poller and close here
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exc):
        self._stop.set()
        try:
            if self.token:
                try:
                    self._req("DELETE", "/_blazor", {"id": self.token}, timeout=10)  # SignalR's own close, ends the poll
                except core.Blocked:
                    raise  # so `paced` records it; this drops rows already rendered, by choice: the cooldown matters more
                except Exception:  # noqa: BLE001 a failed close must not hide the real result
                    pass
        finally:
            if self._poller:
                self._poller.join(2)

    def _next(self, wait):
        try:
            item = self._inbox.get(timeout=wait)
        except queue.Empty:
            return
        if isinstance(item, BaseException):
            raise item
        try:
            self._on_data(item)
        except (ValueError, IndexError, KeyError, TypeError, struct.error) as e:
            raise core.LayoutChanged(f"30book circuit message not understood: {type(e).__name__}: {e}") from e

    def _on_data(self, data):
        if self.handshaking:
            end = data.index(b"\x1e")
            if json.loads(data[:end] or b"{}").get("error"):
                raise CircuitError("30book rejected the protocol handshake")
            data, self.handshaking = data[end + 1:], False
            self._send(invocation("StartCircuit", [self.base + "/", self.url, "[]", self.state], "0"))
        for msg in unframe(data):
            self._handle(msg)

    def _handle(self, msg):
        kind = msg[0]
        if kind == 3 and msg[2] == "0":  # StartCircuit completed: [3, {}, id, resultKind, result]
            if msg[3] == 1:
                raise CircuitError(f"30book circuit error: {msg[4]}")
            if len(msg) < 5 or not msg[4]:
                raise CircuitError("30book did not start a circuit")
            ops = [{"type": "add", "ssrComponentId": i + 1, "marker": m} for i, m in enumerate(self.markers)]
            payload = json.dumps({"batchId": 1, "operations": ops}, separators=(",", ":"), ensure_ascii=False)
            self._send(invocation("UpdateRootComponents", [payload, self.state]))
        elif kind == 7:
            raise CircuitError("30book closed the circuit")
        elif kind == 1:
            target, args = msg[3], msg[4]
            if target == "JS.AttachComponent":
                self.dom.attach_root(args[0], int(args[1]))
            elif target == "JS.RenderBatch":
                self.dom.apply(args[1])
                self.batches += 1
                self.last_batch = time.monotonic()
                self._send(invocation("OnRenderCompleted", [args[0], None]))
            elif target == "JS.BeginInvokeJS" and args[0]:  # a JS call the server awaits: answer null
                self._send(invocation("EndInvokeJSFromDotNet", [args[0], True, f"[{args[0]},true,null]"]))

    @property
    def roots(self):
        return [self.dom.roots[k] for k in sorted(self.dom.roots)]

    def wait(self, ready, settle=0.5):
        """Pump messages until `ready(roots)` holds and no batch arrived for `settle` seconds, within the deadline."""
        while time.monotonic() < self.deadline:
            self._next(0.1)
            if self.batches >= 2 and ready(self.roots) and time.monotonic() - self.last_batch >= settle:
                return self.roots
        raise CircuitError("30book did not render the page in time")


def take_cookies(jar, reply):
    for c in (getattr(reply, "get_all", lambda k: None)("Set-Cookie") or []):
        name, _, rest = c.partition("=")
        jar[name.strip()] = rest.split(";")[0]


def render(store, url, ready, timeout=TIMEOUT):
    """The root component trees of `url` once `ready(roots)` holds: one paced session, no retry, `timeout` overall."""
    u = urlparse(url)
    base, jar = f"{u.scheme}://{u.netloc}", {}
    with core.session(store):
        deadline = time.monotonic() + timeout  # after the lock wait and pace gap, so queued runs keep their full budget
        _, body, reply = core.raw(url, store=store, headers={"Accept": "text/html"}, pace=False, timeout=max(1, min(25, timeout)))
        take_cookies(jar, reply)
        html = body.decode("utf-8", "replace")
        if not page_markers(html)[0]:  # no circuit to open: a bot check page, or the layout changed
            if core.BOT_CHECK.search(html[:5000]):
                raise core.Blocked("30book page is a bot check (no Blazor components)")
            raise core.LayoutChanged("30book page has no interactive Blazor components")
        with Circuit(store, base, url, html, jar, deadline) as c:
            return c.wait(ready)

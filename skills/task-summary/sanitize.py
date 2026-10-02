#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Reduce third-party tracker HTML to inert markup before it goes into a page.

Keeps the text and structure of a description or comment; drops everything
that can run, restyle the page, or load a resource. Allowlist, not denylist:
an unknown tag loses its markup and keeps its text.

Usage:
  sanitize.py < raw.html > clean.html   Exit 1 when an <img> had no data: URI.
  sanitize.py selftest                  Run the built-in checks.
"""

from __future__ import annotations

import sys
from html import escape
from html.parser import HTMLParser

KEEP = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup",
    "dd", "del", "div", "dl", "dt", "em", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd", "li",
    "mark", "ol", "p", "pre", "q", "s", "small", "span", "strike", "strong",
    "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
VOID = {"br", "col", "hr", "img"}
# Elements whose content is code, chrome or embedded media, never readable text.
DROP_CONTENT = {
    "script", "style", "iframe", "frame", "frameset", "object", "embed", "applet",
    "template", "noscript", "svg", "math", "textarea", "select", "title", "head",
    "audio", "video", "canvas",
}
ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "ol": {"start"},
}
SAFE_HREF = ("http://", "https://", "mailto:", "#")


def _squash(value: str) -> str:
    return "".join(ch for ch in value if ch > " ").lower()


class Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.skip = 0
        self.missing_images = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in KEEP:
            return
        kept = []
        for name, value in attrs:
            if name not in ATTRS.get(tag, ()) or value is None:
                continue
            if name == "href" and not _squash(value).startswith(SAFE_HREF):
                continue
            if name == "src" and not _squash(value).startswith("data:image/"):
                continue
            kept.append(f' {name}="{escape(value)}"')
        if tag == "img" and not any(a.startswith(' src="') for a in kept):
            self.missing_images += 1
            self.out.append("[image not embedded]")
            return
        if tag == "a" and kept:
            kept.append(' rel="noopener noreferrer"')
        self.out.append(f"<{tag}{''.join(kept)}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in DROP_CONTENT:
            self.skip -= 1

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in self.open:
            return
        while self.open:
            top = self.open.pop()
            self.out.append(f"</{top}>")
            if top == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        self.close()
        return "".join(self.out) + "".join(f"</{t}>" for t in reversed(self.open))


def sanitize(raw: str) -> tuple[str, int]:
    s = Sanitizer()
    s.feed(raw)
    return s.result(), s.missing_images


def selftest() -> int:
    png = "data:image/png;base64,iVBORw0KGgo="
    cases = [
        ("script dropped, text kept", "<p>hi<script>alert(1)</script></p>", "<p>hi</p>", 0),
        ("style element and attribute dropped",
         '<style>body{display:none}</style><p style="position:fixed">x</p>', "<p>x</p>", 0),
        ("event handlers dropped, any case", '<b ONCLICK="x()" onmouseover=y>t</b>', "<b>t</b>", 0),
        ("remote img becomes a flagged placeholder",
         '<img src="https://evil.example/p.png" onerror="x()">', "[image not embedded]", 1),
        ("data: img kept", f'<img src="{png}" alt="a">', f'<img src="{png}" alt="a">', 0),
        ("javascript: href dropped despite case and whitespace",
         '<a href=" JaVa\tScRiPt:alert(1)">l</a>', "<a>l</a>", 0),
        ("https href kept with noopener",
         '<a href="https://x.test/a?b=1&amp;c=2">l</a>',
         '<a href="https://x.test/a?b=1&amp;c=2" rel="noopener noreferrer">l</a>', 0),
        ("iframe, object, form controls dropped",
         ('<iframe src="https://x.test"></iframe><object data="x"></object>'
          '<form action="https://x.test"><input name="p">ok<button>go</button></form>'), "okgo", 0),
        ("stray close tag cannot escape the container", "<p>a</p></div></div><p>b", "<p>a</p><p>b</p>", 0),
        ("unclosed tags are closed", "<ul><li><b>x", "<ul><li><b>x</b></li></ul>", 0),
        ("escaped text stays escaped", "<p>&lt;script&gt;1 &amp; 2</p>", "<p>&lt;script&gt;1 &amp; 2</p>", 0),
        ("comments and ids dropped", '<!-- x --><div id="desc" class="callout">t</div>', "<div>t</div>", 0),
        ("self-closed svg drops nothing after it", "<svg/><p>t</p>", "<p>t</p>", 0),
    ]
    fails = 0
    for name, raw, want, want_missing in cases:
        got, missing = sanitize(raw)
        ok = got == want and missing == want_missing
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n  want {want!r} ({want_missing})\n  got  {got!r} ({missing})"))
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "selftest":
        return selftest()
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    clean, missing = sanitize(sys.stdin.read())
    sys.stdout.write(clean)
    if missing:
        print(f"sanitize: {missing} <img> without a data: URI became '[image not embedded]'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

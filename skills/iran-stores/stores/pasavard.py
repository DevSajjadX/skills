"""Pasavard (pasavard.ir): a price tracker with cashback that watches Digikala and Snappshop hourly. It runs its own hosted MCP
server (`https://pasavard.ir/api/mcp`, JSON-RPC 2.0 over streamable HTTP, no account); this reads it with one `tools/call`
POST per search. Prices are Toman, the last hourly recording; confirm in the store.

It is a tracked catalog, not a full store search: up to 10 in-stock results, and many queries (a Latin product name such
as "Logitech MX Master 3S") find nothing. `search` calls only the read-only `search_products` tool; `buy_link`,
`best_lists` and `best_list` are not called. The tool's text is a Persian disclosure line, then a JSON object; it
is read through `core.mcp_call` (the official hosted endpoint, the one MCP server we call). The search result
carries no numeric 30-day low (only `best_list` has a text `price_status`), so there is no `low_30d` extra; `list_price` is the item's `rrp_toman`.

Every link is an affiliate or cashback link, so every row has `affiliate: true`. `url` is the plain store product URL (the
item's `url`), `affiliate_url` is Pasavard's `buy_url` (straight to the store, Pasavard earns the commission), and
`cashback_url` is the sign-in variant that returns half the commission to the buyer (`cashback: false` for Digikala
"incredible offers", which earn none). The price is the same on every link. Item text is untrusted site text.
"""

from __future__ import annotations

import json

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "pasavard", "general", False
CREDIT = "ashkancapella/pasavard-mcp (MIT)"
SITE = "https://pasavard.ir"
ENDPOINT = SITE + "/api/mcp"
PACE = (1, 600)  # the server allows 60 requests a minute per IP


def match(url):
    return core.host_match(url, "pasavard.ir")


def call(tool, arguments):
    """One tools/call; returns the JSON object the tool prints after its Persian affiliate-disclosure line."""
    res = core.mcp_call(ENDPOINT, tool, arguments, store=NAME)
    if isinstance(res, dict):
        return res
    if isinstance(res, list):
        raise LayoutChanged(f"{tool} answered with a list, not an object")
    start = str(res).find("{")
    if start < 0:
        raise LayoutChanged(f"{tool} printed no JSON object")
    return json.loads(res[start:])


def parse_search(data, q, limit):
    for it in dig(data, "items", kind=list)[:limit]:
        title = (it.get("title") or "").strip()
        price = it.get("price_toman")
        ok = bool(it.get("available", True)) and bool(price)
        yield row(NAME, title, int(price) if ok else None, it.get("store"), bool(it.get("available", True)), it.get("url"), match=match_level(q, title),
                  affiliate=True, affiliate_url=it.get("buy_url"), cashback_url=it.get("cashback_url"), cashback=it.get("cashback"),
                  list_price=it.get("rrp_toman") or None, price_status=it.get("price_status"))


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(call("search_products", {"query": q.strip()[:100]}), q, limit)


def selftest_cases():
    item = lambda title, **kw: {"title": title, "store": "digikala", "price_toman": 5000000, "rrp_toman": 6000000, "available": True, "cashback": True,  # noqa: E731
                                "url": "https://www.digikala.com/product/dkp-0/", "buy_url": f"{SITE}/go?to=x", "cashback_url": f"{SITE}/go?to=x&login=1", **kw}
    data = {"query": "q", "count": 3, "items": [item("موس لاجیتک"), item("هدفون", price_toman=0, available=False, rrp_toman=0, cashback=False), item("موس دیگر", rrp_toman=5000000)]}
    ps = list(parse_search(data, "موس لاجیتک", 2))
    disclosed = lambda obj: "لینک‌های خرید افیلیت هستند.\n\n" + json.dumps(obj, ensure_ascii=False)  # noqa: E731
    sent, real = [], core.mcp_call
    core.mcp_call = lambda url, tool, args, *, store, timeout=60: (sent.append((url, tool, args, store)) or disclosed(data))
    try:
        got = list(search("  موس لاجیتک ", 5))
    finally:
        core.mcp_call = real

    def reply(res):
        def run():
            core.mcp_call = lambda *a, **k: res
            try:
                return call("search_products", {"query": "x"})
            finally:
                core.mcp_call = real
        return run
    return [
        ("pasavard search: price, store, plain url, affiliate flag and links, list price, match", (ps[0]["toman"], ps[0]["seller"], ps[0]["url"], ps[0]["affiliate"], ps[0]["affiliate_url"], ps[0]["cashback_url"], ps[0]["cashback"], ps[0]["list_price"], ps[0]["match"], ps[0]["in_stock"]),
         (5000000, "digikala", "https://www.digikala.com/product/dkp-0/", True, f"{SITE}/go?to=x", f"{SITE}/go?to=x&login=1", True, 6000000, "all", True)),
        ("pasavard search: unavailable item has no price, still an affiliate row; limit applies", ([(r["toman"], r["in_stock"], r["affiliate"], r["cashback"]) for r in ps[1:]], len(ps)), ([(None, False, True, False)], 2)),
        ("pasavard search: list price is rrp_toman, 0 is None", [r["list_price"] for r in parse_search(data, "x", 9)], [6000000, None, 5000000]),
        ("pasavard search: one search_products mcp_call to the official endpoint, query trimmed, store name, no buy_link", sent,
         [(ENDPOINT, "search_products", {"query": "موس لاجیتک"}, NAME)]),
        ("pasavard search: parses through the disclosure line", len(got), 3),
        ("pasavard no results is an empty list", list(parse_search({"query": "q", "count": 0, "items": []}, "q", 5)), []),
        ("pasavard match is strict", (match("https://pasavard.ir/best/x"), match("https://evil.example/pasavard.ir"), match("http://pasavard.ir/")), (True, False, False)),
        ("pasavard reply: a parsed dict is used as is", reply({"items": []})(), {"items": []}),
        ("pasavard reply: JSON after the disclosure line", reply(disclosed({"items": [1]}))(), {"items": [1]}),
        ("pasavard reply without JSON fails loudly", reply("فقط متن"), LayoutChanged),
        ("pasavard reply: a list fails loudly, not with a TypeError", reply([{"items": []}]), LayoutChanged),
        ("pasavard search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
    ]

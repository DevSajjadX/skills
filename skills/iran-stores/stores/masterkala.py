"""MasterKala (masterkala.com): JSON routes at /api/2.1.1.0.0/?route=... plus server-rendered product pages.

Search and review prices are Toman strings ('4508000.0000'); the product page's inline state is Toman and
its JSON-LD offers are Rial. A single-seller shop: `offers` reports the product's price and its variants.
No installment data is read by the reference, so there is no `installments`.
"""

from __future__ import annotations

import html
import json
import re

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "masterkala", "electronics", False
CREDIT = "sepehr071/masterkala-mcp (MIT)"
BASE = "https://masterkala.com"
API = f"{BASE}/api/2.1.1.0.0/"
# The site sends the JSON as text/plain with an empty Authorization header for guests.
HEADERS = {"Accept": "application/json, text/plain, */*", "Authorization": "", "Content-Type": "text/plain;charset=UTF-8",
           "Origin": BASE, "Referer": BASE + "/"}
OPTION_NAMES = {"14": "color", "15": "warranty"}
PAGE = 25  # reviews per API call


def match(url):
    return core.host_match(url, "masterkala.com")


def api(route, body):
    # The review routes POST a review when the body carries `data`: this reader never sends it.
    if "data" in body:
        raise ValueError("refusing to send a `data` object: it would post a review")
    data = json.loads(core.post_json(f"{API}?route={route}", body, HEADERS, store=NAME))
    if data is None:
        raise ValueError(f"masterkala.com returned no data for {route}; check the id")
    if isinstance(data, dict) and data.get("success") == "0":
        raise ValueError(f"masterkala.com rejected the request: {str(data.get('message') or data)[:200]}")
    return data


def product_id(ref):
    m = re.search(r"/product/(\d{1,8})", ref) or re.fullmatch(r"\s*(\d{1,8})\s*", ref)
    if not m:
        raise ValueError(f"not a MasterKala product URL or id: {ref}")
    return int(m.group(1))


def toman(v):
    """API prices are Toman strings like '4508000.0000'; 0 means not sold online."""
    try:
        return int(float(v or 0)) or None
    except (TypeError, ValueError):
        return None


def search_body(q, limit):
    return {"v": "1.2", "query": q.strip(), "from": 0, "limit": limit, "filter": ""}


def reviews_body(pid, offset=0):
    return {"product_id": str(pid), "from": offset, "limit": PAGE, "rating": 0}  # never a `data` key


def parse_search(data, q, limit):
    for p in dig(data, "products", kind=list)[:limit]:
        if not p.get("product_id"):
            continue
        final, price = toman(p.get("pricewithdiscount")), toman(p.get("price"))
        ok = p.get("quantity") == "1" and final is not None
        label = p.get("top_label")
        yield row(NAME, (p.get("name") or "").strip(), final if ok else None, None, ok,
                  f"{BASE}/product/{p['product_id']}/{p.get('slug') or 'x'}", match=match_level(q, p.get("name")),
                  discount=int(p.get("percent") or 0) if final and price and final < price else 0,
                  note=(p.get("stock_status") or "").strip() if not ok else None,
                  label=label.get("title") if isinstance(label, dict) else None)


def parse_offers(doc, url):
    item = next((x for x in core.json_ld(doc) if x.get("@type") == "Product"), None)
    if item is None:
        raise LayoutChanged("no Product JSON-LD on the page")
    offer = item.get("offers")
    offer = offer[0] if isinstance(offer, list) and offer else offer
    prices = re.search(r"price: ([\d.]+),\s*price_with_discount: ([\d.]+)", doc)
    if prices:
        final = int(float(prices.group(2)))
    else:
        final = core.rial_to_toman((offer.get("lowPrice") if isinstance(offer, dict) else None)) or 0  # Rial here
    badge = core.first(r'rounded-bl-2xl px-3 py-5 w-fit text-xs text-white[^"]*">\s*([^<]+?)\s*</div>', doc)
    avail = offer.get("availability") if isinstance(offer, dict) else None
    if not avail and badge is None:
        raise LayoutChanged("no offers.availability in the JSON-LD and no stock badge")
    in_stock = bool(final) and (str(avail).rsplit("/", 1)[-1].lower() == "instock" if avail else badge is None)  # the badge is only a note
    raw = core.first(r"\n\s*optionList: (\[.*?\]),\n", doc)
    state = core.first(r"\n\s*available: (\{.*?\}),\n", doc)
    try:
        buyable = {str(v) for v in json.loads(state).get("option_values_available") or []} if state else set()
        options = [{"name": OPTION_NAMES.get(o.get("option_id"), (o.get("name") or "").strip()),
                    "values": [{"name": (v.get("name") or "").strip(), "available": v.get("option_value_id") in buyable}
                               for v in o.get("product_option_value") or []]}
                   for o in (json.loads(raw) if raw else [])]
    except (ValueError, AttributeError) as e:
        raise LayoutChanged(f"option state is not JSON: {e}") from e
    yield row(NAME, item.get("name"), final if in_stock else None, "MasterKala", in_stock, url,
              note=badge or (None if in_stock else "no price"), options=options or None)


def parse_reviews(pages, url):
    """`pages` are API bodies in order; the first carries count and the star breakdown."""
    first_page = pages[0]
    groups = {int(g["rating"]): int(g["count"]) for g in dig(first_page, "rating_group", kind=list)}
    total = sum(groups.values())
    yield {"store": NAME, "url": url, "kind": "summary", "count": int(first_page.get("count") or 0),
           "average": round(sum(r * n for r, n in groups.items()) / total, 2) if total else None,
           "star_counts": {str(r): groups.get(r, 0) for r in range(5, 0, -1)}}
    rows = [r for p in pages for r in dig(p, "list", kind=list)]
    for r in sorted(rows, key=lambda r: r.get("date_added") or "", reverse=True):
        reply = html.unescape((r.get("reply") or "").strip())
        yield {"store": NAME, "url": url, "stars": int(r.get("rating") or 0) or None, "text": (r.get("text") or "").strip(),
               "date": (r.get("date_added") or "")[:10] or None, "verified": bool(r.get("order_id")) if "order_id" in r else None,
               "pros": None, "cons": None, "reply": reply or None, "likes": None}


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(api("product/searchproduct", search_body(q, limit)), q, limit)


def offers(url):
    pid = product_id(url)
    page = f"{BASE}/product/{pid}/x"  # any slug redirects to the canonical one
    yield from parse_offers(core.get(page, store=NAME), page)


def reviews(url, limit):
    pid = product_id(url)
    pages = [api("productreview/getproductreviews", reviews_body(pid))]
    count = int(pages[0].get("count") or 0)
    for off in range(PAGE, min(limit, count, 4 * PAGE), PAGE):
        pages.append(api("productreview/getproductreviews", reviews_body(pid, off)))
    out = list(parse_reviews(pages, f"{BASE}/product/{pid}/x"))
    yield from out[:1 + limit]


def selftest_cases():
    sr = {"count": "3", "products": [
        {"product_id": "0", "name": "محصول نمونه", "slug": "mx", "price": "5000000.0000", "pricewithdiscount": "4500000.0000", "percent": 10,
         "quantity": "1", "stock_status": "موجود", "top_label": {"title": "خرید حضوری"}},
        {"product_id": "1", "name": "محصول ناموجود", "price": "0.0000", "pricewithdiscount": "0.0000", "percent": 0, "quantity": "0",
         "stock_status": "ناموجود"},
        {"name": "بدون شناسه"}]}
    ld = json.dumps({"@type": "Product", "name": "ماوس", "offers": {"lowPrice": "45000000", "availability": "https://schema.org/InStock"}})
    ld_out = json.dumps({"@type": "Product", "name": "ماوس", "offers": {"lowPrice": "45000000", "availability": "https://schema.org/OutOfStock"}})
    ld_none = json.dumps({"@type": "Product", "name": "ماوس", "offers": {"lowPrice": "45000000"}})
    doc = (f'<script type="application/ld+json">{ld}</script>\n        optionList: '
           '[{"option_id":"14","name":"رنگ","product_option_value":[{"option_value_id":"53","name":"سفید "},{"option_value_id":"52","name":"مشکی"}]}],\n'
           '        available: {"option_values_available":[53]},\n      price: 5000000.0000,\n      price_with_discount: 4500000.0000,\n')
    badge = '<div class="rounded-bl-2xl px-3 py-5 w-fit text-xs text-white bg"> ناموجود </div>'
    out_doc = f'<script type="application/ld+json">{ld}</script>' + badge  # availability InStock outranks the badge
    avail_out = f'<script type="application/ld+json">{ld_out}</script>'
    no_price_doc = f'<script type="application/ld+json">{ld_none}</script>' + badge
    rv = [{"count": "3", "rating_group": [{"rating": "4", "count": "1"}, {"rating": "5", "count": "2"}], "list": [
        {"rating": "4", "text": "خوب", "date_added": "2024-01-03 04:05:06", "reply": "", "order_id": "0", "author": "کاربر"},
        {"rating": "5", "text": "عالی\r\n", "date_added": "2024-01-01 02:03:04", "reply": "ممنون", "order_id": "0"}]},
        {"list": [{"rating": "5", "text": "نو", "date_added": "2024-07-01 10:00:00", "reply": ""}]}]
    ps, po = list(parse_search(sr, "محصول", 9)), list(parse_offers(doc, "u"))
    pr = list(parse_reviews(rv, "u"))
    sent = []
    real = core.post_json
    core.post_json = lambda url, body, headers=None, store=None: (sent.append((url, body, headers, store)) or "{}")
    try:
        api("productreview/getproductreviews", reviews_body(5))
    finally:
        core.post_json = real
    return [
        ("masterkala search: price, discount, match, label", ps[0], row(NAME, "محصول نمونه", 4500000, None, True, "https://masterkala.com/product/0/mx",
                                                                       match="all", discount=10, note=None, label="خرید حضوری")),
        ("masterkala search: out of stock has no price", (ps[1]["toman"], ps[1]["in_stock"], ps[1]["note"], ps[1]["url"]),
         (None, False, "ناموجود", "https://masterkala.com/product/1/x")),
        ("masterkala search: card without an id is skipped", len(ps), 2),
        ("masterkala offers: inline Toman price and variants", (po[0]["toman"], po[0]["in_stock"], po[0]["options"]),
         (4500000, True, [{"name": "color", "values": [{"name": "سفید", "available": True}, {"name": "مشکی", "available": False}]}])),
        ("masterkala offers: JSON-LD availability decides stock, the badge is only the note", [(r["toman"], r["in_stock"], r["note"]) for r in parse_offers(out_doc, "u")], [(45000000 // 10, True, "ناموجود")]),
        ("masterkala offers: JSON-LD OutOfStock means no price, no badge needed", [(r["toman"], r["in_stock"], r["note"]) for r in parse_offers(avail_out, "u")], [(None, False, "no price")]),
        ("masterkala offers: no availability but a badge is out of stock", [(r["toman"], r["in_stock"], r["note"]) for r in parse_offers(no_price_doc, "u")], [(None, False, "ناموجود")]),
        ("masterkala offers: neither availability nor a badge fails loudly", lambda: list(parse_offers(f'<script type="application/ld+json">{ld_none}</script>', "u")), LayoutChanged),
        ("masterkala reviews: summary first", pr[0], {"store": NAME, "url": "u", "kind": "summary", "count": 3, "average": 4.67,
                                                      "star_counts": {"5": 2, "4": 1, "3": 0, "2": 0, "1": 0}}),
        ("masterkala reviews: newest first across pages, reply kept", [(r["stars"], r["date"], r["reply"], r["verified"]) for r in pr[1:]],
         [(5, "2024-07-01", None, None), (4, "2024-01-03", None, True), (5, "2024-01-01", "ممنون", True)]),
        ("masterkala reviews request body has no data key", ("data" in sent[0][1], sent[0][1], sent[0][0], sent[0][3]),
         (False, {"product_id": "5", "from": 0, "limit": 25, "rating": 0}, f"{API}?route=productreview/getproductreviews", NAME)),
        ("masterkala api refuses a body with data", lambda: api("productreview/getproductreviews", {"product_id": "1", "data": {}}), ValueError),
        ("masterkala search body is read-only shaped", search_body(" mx ", 5), {"v": "1.2", "query": "mx", "from": 0, "limit": 5, "filter": ""}),
        ("masterkala product id from URL and number", (product_id("https://masterkala.com/product/6/x"), product_id("7")), (6, 7)),
        ("masterkala match is strict", (match("https://masterkala.com/product/1/x"), match("https://evil.example/masterkala.com"), match("http://masterkala.com/")),
         (True, False, False)),
        ("masterkala bad product ref fails", lambda: product_id("https://masterkala.com/"), ValueError),
        ("masterkala search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("masterkala offers layout change fails loudly", lambda: list(parse_offers("<html></html>", "u")), LayoutChanged),
        ("masterkala reviews layout change fails loudly", lambda: list(parse_reviews([{"list": []}], "u")), LayoutChanged),
    ]

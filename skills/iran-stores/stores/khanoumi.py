"""Khanoumi (khanoumi.com): JSON REST under /api/ntl/v1 (catalog) and /api/cml/v1 (comments). Prices are Toman.

Comments carry no star rating (the product's average is in the product record), a verified-buyer flag
and optional photos. The reference reads no installment data, so there is no `installments`.
Every request here is a GET; nothing writes a comment, cart or account.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "khanoumi", "beauty", False
CREDIT = "sepehr071/khanoumi-mcp (MIT)"
BASE = "https://www.khanoumi.com"
HEADERS = {"Accept": "application/json, text/html;q=0.9", "Referer": BASE + "/"}
MAX_COMMENTS = 100  # the API's page size cap in the reference


def match(url):
    return core.host_match(url, "khanoumi.com")


def api(path, **params):
    q = urlencode({k: v for k, v in params.items() if v is not None})
    body = core.get_json(f"{BASE}{path}" + (f"?{q}" if q else ""), HEADERS, store=NAME)
    if not isinstance(body, dict) or "data" not in body:
        raise LayoutChanged(f"{path} did not answer with an envelope")
    if body.get("isSuccess") is False:
        raise ValueError(f"khanoumi.com rejected the request for {path}")
    if body["data"] is None:
        raise ValueError(f"khanoumi.com has nothing for {path}; check the product")
    return body["data"]


def product_ref(ref):
    """('slug', slug) or ('id', id) from a product URL, a slug or a bare id."""
    path = urlparse(ref).path if "://" in ref else ref
    m = re.search(r"/products/([A-Za-z0-9-]*\d)/?$", path) or re.fullmatch(r"\s*([A-Za-z0-9-]*\d)\s*", path)
    if not m:
        raise ValueError(f"not a Khanoumi product URL, slug or id: {ref}")
    return ("id" if m.group(1).isdigit() else "slug"), m.group(1)


def product(ref):
    kind, v = product_ref(ref)
    if kind == "id":
        v = dig(api(f"/api/ntl/v1/products/id/{v}"), "slug")
    return api(f"/api/ntl/v1/products/slug/{v}")


def product_url(slug):
    return f"{BASE}/products/{slug}"


def price_of(final, salable):
    """Toman payable; None when the item cannot be ordered or has no price."""
    return (final or None) if salable else None


def parse_search(data, q, limit):
    for p in dig(data, "products", "items", kind=list)[:limit]:
        if not p.get("id") or not p.get("slug"):
            continue
        ok = bool(p.get("isSalable"))
        final, base = p.get("effectivePrice"), p.get("basePrice")
        title = (p.get("nameFa") or "").strip()
        flags = [f for f in (s.strip() for s in (p.get("flags") or "").split(",")) if f and f != "None"]
        yield row(NAME, title, price_of(final, ok), None, ok and bool(final), product_url(p["slug"]), match=match_level(q, title),
                  ad=bool(p.get("ad")), discount=core.discount_pct(final, base),
                  brand=(p.get("brand") or {}).get("nameFa"), shades=p["colorsCount"] if (p.get("colorsCount") or 0) > 1 else None,
                  badges=flags or None)


def parse_offers(p, url):
    """One row per shade/size/seller variant; the card has no rating, the product record does."""
    title = (dig(p, "nameFa") or "").strip()
    rating = p.get("rate") if p.get("ratesCount") else None
    for v in dig(p, "variants", kind=list):
        ok = bool(v.get("isSalable"))
        final = v.get("salesPrice")
        size = f"{v['weight']['value']} {v['weight'].get('unit') or ''}".strip() if (v.get("weight") or {}).get("value") else None
        yield row(NAME, title, price_of(final, ok), v.get("vendorDisplayName") or "خانومی", ok and bool(final), url,
                  variant=(v.get("color") or {}).get("name") or size, rating=rating, rating_count=p.get("ratesCount") or None,
                  discount=int(v.get("discountPercent") or 0), max_qty=v.get("limit"), lead_days=v.get("leadTime"))


def parse_reviews(p, comments, url):
    yield {"store": NAME, "url": url, "kind": "summary", "count": dig(comments, "totalCount"),
           "average": p.get("rate") if p.get("ratesCount") else None, "rating_count": p.get("ratesCount") or 0,
           "note": "comments have no stars; the average is the product's rating"}
    for c in dig(comments, "items", kind=list):
        yield {"store": NAME, "url": url, "stars": None, "text": (c.get("description") or "").strip(), "date": (c.get("createdAt") or "")[:10] or None,
               "verified": bool(c["isBuyer"]) if "isBuyer" in c else None, "pros": None, "cons": None, "reply": None,
               "likes": c.get("likeCount"), "photos": c.get("imageUrls") or []}


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(api("/api/ntl/v1/products", query=q.strip(), page_number=1, page_size=limit), q, limit)


def offers(url):
    p = product(url)
    yield from parse_offers(p, product_url(dig(p, "slug")))


def reviews(url, limit):
    p = product(url)
    link = product_url(dig(p, "slug"))
    comments = api(f"/api/cml/v1/products/id/{dig(p, 'id')}/comments", page_number=1, page_size=max(1, min(limit, MAX_COMMENTS)))
    yield from parse_reviews(p, comments, link)


def selftest_cases():
    sr = {"products": {"items": [
        {"id": "0", "slug": "cream-0", "nameFa": "کرم ضد آفتاب تست", "isSalable": True, "basePrice": 1000000, "effectivePrice": 800000,
         "discountPercent": 20, "colorsCount": 3, "flags": "Chance, New", "brand": {"nameFa": "برند"}, "ad": None},
        {"id": "1", "slug": "cream-1", "nameFa": "ناموجود", "isSalable": False, "basePrice": 500000, "effectivePrice": 500000, "discountPercent": 0,
         "colorsCount": 1, "flags": "", "ad": True},
        {"nameFa": "بدون شناسه"}]}}
    pv = {"id": "0", "slug": "cream-0", "nameFa": "کرم تست", "rate": 4.5, "ratesCount": 8, "variants": [
        {"id": "1", "color": {"name": "بژ"}, "isSalable": True, "salesPrice": 800000, "discountPercent": 20, "limit": 3, "leadTime": 0},
        {"id": "2", "weight": {"value": 50, "unit": "ml"}, "isSalable": False, "salesPrice": 700000, "vendorDisplayName": "فروشنده"}]}
    cm = {"totalCount": 2, "items": [
        {"description": " خوب بود ", "likeCount": 1, "isBuyer": True, "createdAt": "2026-10-02T03:04:05+03:30", "imageUrls": ["https://example.com/a.webp"]},
        {"description": "بد", "likeCount": 0, "isBuyer": False, "createdAt": "2026-10-10T00:00:00+03:30", "imageUrls": []}]}
    ps, po, pr = list(parse_search(sr, "ضد آفتاب", 9)), list(parse_offers(pv, "u")), list(parse_reviews(pv, cm, "u"))
    seen, real_get_json = [], core.get_json
    answers = {"/api/ntl/v1/products/id/7": {"data": {"slug": "cream-0"}}, "/api/ntl/v1/products/slug/cream-0": {"data": pv}}
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, store)) or answers[urlparse(url).path])
    try:
        by_id, by_url = product("7"), product("https://www.khanoumi.com/products/cream-0")
    finally:
        core.get_json = real_get_json
    core.get_json = lambda url, headers=None, store=None: {"isSuccess": True, "data": None}
    try:
        empty = lambda: api("/api/ntl/v1/products/slug/x")  # noqa: E731
        empty_ok = False
        try:
            empty()
        except ValueError:
            empty_ok = True
    finally:
        core.get_json = real_get_json
    return [
        ("khanoumi search: price, discount, shades, badges, match", ps[0], row(NAME, "کرم ضد آفتاب تست", 800000, None, True, f"{BASE}/products/cream-0", match="all",
                                                                              ad=False, discount=20, brand="برند", shades=3, badges=["Chance", "New"])),
        ("khanoumi search: out of stock has no price and keeps the ad flag", (ps[1]["toman"], ps[1]["in_stock"], ps[1]["ad"], ps[1]["discount"]), (None, False, True, 0)),
        ("khanoumi search: card without an id is skipped", len(ps), 2),
        ("khanoumi offers: shade variant", (po[0]["variant"], po[0]["toman"], po[0]["in_stock"], po[0]["seller"], po[0]["rating"]), ("بژ", 800000, True, "خانومی", 4.5)),
        ("khanoumi offers: out-of-stock size has no price", (po[1]["variant"], po[1]["toman"], po[1]["in_stock"], po[1]["seller"]), ("50 ml", None, False, "فروشنده")),
        ("khanoumi reviews: summary first", {k: pr[0][k] for k in ("kind", "count", "average", "rating_count")}, {"kind": "summary", "count": 2, "average": 4.5, "rating_count": 8}),
        ("khanoumi reviews: buyer flag, photos, date", [(r["text"], r["verified"], r["photos"], r["date"], r["stars"]) for r in pr[1:]],
         [("خوب بود", True, ["https://example.com/a.webp"], "2026-10-02", None), ("بد", False, [], "2026-10-10", None)]),
        ("khanoumi product by id resolves the slug, by url reads it", ([u for u, _ in seen], by_id["slug"], by_url["slug"], {s for _, s in seen}),
         ([f"{BASE}/api/ntl/v1/products/id/7", f"{BASE}/api/ntl/v1/products/slug/cream-0", f"{BASE}/api/ntl/v1/products/slug/cream-0"], "cream-0", "cream-0", {NAME})),
        ("khanoumi empty data is an error", empty_ok, True),
        ("khanoumi product ref forms", (product_ref("https://www.khanoumi.com/products/cream-0"), product_ref("cream-0"), product_ref("1")),
         (("slug", "cream-0"), ("slug", "cream-0"), ("id", "1"))),
        ("khanoumi match is strict", (match("https://www.khanoumi.com/products/x-1"), match("https://evil.example/khanoumi.com"), match("http://khanoumi.com/")), (True, False, False)),
        ("khanoumi bad ref fails", lambda: product_ref("https://www.khanoumi.com/"), ValueError),
        ("khanoumi search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("khanoumi offers layout change fails loudly", lambda: list(parse_offers({"nameFa": "x"}, "u")), LayoutChanged),
        ("khanoumi reviews layout change fails loudly", lambda: list(parse_reviews(pv, {}, "u")), LayoutChanged),
    ]

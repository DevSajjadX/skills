"""Digikala Fresh (supermarket): groceries from the same API as Digikala. Search only. Prices are Rial."""

from __future__ import annotations

from urllib.parse import urlencode

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, rial_to_toman, row
from stores.digikala import API, HEADERS, SITE, stars

NAME, KIND, DEFAULT = "digikala_fresh", "grocery", False
CREDIT = "sepehr071/digikala-mcp (MIT), endpoints and units re-implemented"


def parse_search(data, q, limit):
    for p in dig(data, "data", "products", kind=list):
        v = p.get("default_variant")
        price = rial_to_toman(((v if isinstance(v, dict) else {}).get("price") or {}).get("selling_price"))
        if p.get("status") != "marketable" or not price:
            continue  # Fresh keeps 'in_supply' items with no offer and no price even with has_selling_stock
        rating = p.get("rating") or {}
        yield row("digikala_fresh", p.get("title_fa") or p.get("title_en"), price, (v.get("seller") or {}).get("title"), True,
                  f"{SITE}/supermarket/product/{p['id']}/", match=match_level(q, f"{p.get('title_fa') or ''} {p.get('title_en') or ''}"),
                  rating=stars(rating.get("rate")), rating_count=rating.get("count") or None)


def search(q, limit, *, at=None, city=None, installment=False):
    data = core.get_json(f"{API}/fresh/v1/search/?" + urlencode({"q": q, "page": 1, "has_selling_stock": 1}), HEADERS, store=NAME)
    for i, r in enumerate(parse_search(data, q, limit)):
        if i >= limit:
            break
        yield r


def selftest_cases():
    fr = {"data": {"products": [
        {"id": 0, "title_fa": "شیر", "status": "marketable", "rating": {"rate": 90, "count": 5},
         "default_variant": {"price": {"selling_price": 280000}, "seller": {"title": "دیجی‌کالا"}}},
        {"id": 1, "title_fa": "ماست", "status": "in_supply", "default_variant": []},
        {"id": 2, "title_fa": "پنیر", "status": "marketable", "default_variant": {"price": {"selling_price": 0}}}]}}
    got = list(parse_search(fr, "شیر", 9))
    return [
        ("fresh row", got[0], row("digikala_fresh", "شیر", 28000, "دیجی‌کالا", True,
                                  "https://www.digikala.com/supermarket/product/0/", match="all", rating=4.5, rating_count=5)),
        ("fresh drops items with no offer or price", len(got), 1),
        ("fresh layout change fails loudly", lambda: list(parse_search({"data": {"products": {}}}, "q", 9)), LayoutChanged),
    ]

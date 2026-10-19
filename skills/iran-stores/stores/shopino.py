"""Shopino (shopino.app): a fashion marketplace, one JSON API (`api-go.shopino.app/api/v1/app/...`). Prices are Toman.

Many shops sell through it, so a row's `seller` is the shop. A search card has no sizes or colours: they come
from `offers` (one row per size/colour variant with its stock). Shopino has no product reviews, so there is no
`reviews`, and the reference reads no installment data. Every request is a GET.
"""

from __future__ import annotations

import re
from urllib.parse import quote, urlencode

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "shopino", "fashion", False
CREDIT = "sepehr071/shopino-mcp (MIT)"
SITE = "https://shopino.app"
API = "https://api-go.shopino.app/api/v1/app"
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}


def match(url):
    return core.host_match(url, "shopino.app")


def api(path, **params):
    q = urlencode({k: v for k, v in params.items() if v is not None})
    data = core.get_json(f"{API}{path}" + (f"?{q}" if q else ""), HEADERS, store=NAME)
    if not isinstance(data, dict):
        raise LayoutChanged(f"{path} did not answer with an object")
    return data


def product_id(ref):
    m = re.search(r"/product/(\d{1,9})", ref) or re.fullmatch(r"\s*(\d{1,9})\s*", ref)
    if not m:
        raise ValueError(f"not a Shopino product URL or id: {ref}")
    return int(m.group(1))


def prices(p):
    """(price payable, price before discount, discount %) in Toman; None when the shop shows no price."""
    price, disc = p.get("price") or 0, p.get("discounted_price") or 0
    final = disc or price
    pct = core.discount_pct(final, price)
    return final or None, (price if pct else final) or None, pct


def parse_search(data, q, limit):
    seen = set()
    for p in dig(data, "results", kind=list):
        if len(seen) >= limit:
            break
        if p.get("id") is None or p["id"] in seen:  # some shops list each colour as its own card with one id
            continue
        seen.add(p["id"])
        final, _, pct = prices(p)
        ok = bool(p.get("in_stock")) and final is not None
        shop = p.get("shop") or {}
        title = (p.get("title") or "").strip()
        yield row(NAME, title, final if ok else None, shop.get("title"), ok, f"{SITE}/product/{p['id']}", match=match_level(q, title),
                  discount=pct, shop_id=shop.get("id"), shop_rating=shop.get("rating") or None, courier_city=shop.get("fast_delivery_city") or None,
                  shop_site_only=True if shop.get("direct_purchase_enabled") is False else None, flash_sale=True if p.get("flash_sale") else None,
                  promo=((p.get("promotion_tag") or {}).get("title") or "").strip() or None)


def parse_offers(p, url):
    """One row per size/colour variant; `in_stock` is the variant's own stock, not the product's."""
    title = (dig(p, "title") or "").strip()
    shop = p.get("shop") or {}
    common = {"shop_id": shop.get("id"), "shop_rating": shop.get("rating") or None, "courier_city": shop.get("fast_delivery_city") or None,
              "shop_site_only": True if shop.get("direct_purchase_enabled") is False else None}
    variations = dig(p, "variations", kind=list)
    if not variations:
        final, _, pct = prices(p)
        ok = bool(p.get("in_stock")) and final is not None
        yield row(NAME, title, final if ok else None, shop.get("title"), ok, url, discount=pct, **common)
        return
    for v in variations:
        final, _, pct = prices(v)
        stock = v.get("stock_quantity")
        ok = bool(stock) and final is not None
        label = ", ".join(f"{a.get('name')}: {a.get('option')}" for a in v.get("attributes") or [])
        yield row(NAME, title, final if ok else None, shop.get("title"), ok, url, variant=label or None, discount=pct, stock=stock, **common)


def parse_seller(s):
    survey = s.get("survey_report") or {}
    pct = lambda k: round(survey[k]) if survey.get(k) is not None else None  # noqa: E731
    customer = s.get("customer_rating") or {}
    return {"store": NAME, "seller": dig(s, "title"), "rating": s.get("rating") or None, "votes": s.get("surveys_count") or 0, "since": None,
            "on_time_pct": pct("positive_timely_delivery"), "returns_pct": None, "seal": "verified" if s.get("is_verified") else None,
            "satisfied_pct": pct("customer_satisfaction"), "good_quality_pct": pct("positive_high_quality"), "good_price_pct": pct("positive_low_price"),
            "customer_rating": customer.get("value"), "customer_rating_count": customer.get("count"), "followers": s.get("followers") or None,
            "products": s.get("products_count"), "courier_city": s.get("fast_delivery_city") or None,
            "shopino_cart": s.get("direct_purchase_enabled"), "website": s.get("website") or None, "url": f"{SITE}/shops/{s.get('id')}"}


def shop_ref(ref):
    m = re.search(r"/shops/([A-Za-z0-9_][A-Za-z0-9._]{0,59})", ref) or re.fullmatch(r"\s*([A-Za-z0-9_][A-Za-z0-9._]{0,59})\s*", ref)
    if not m:
        raise ValueError(f"not a Shopino shop id, username or URL: {ref}")
    return m.group(1)


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(api(f"/products/search/{quote(q.strip(), safe='')}/", page_size=limit), q, limit)


def offers(url):
    pid = product_id(url)
    yield from parse_offers(api(f"/products/{pid}/"), f"{SITE}/product/{pid}")


def seller(ref):
    return parse_seller(api(f"/shops/{shop_ref(ref)}/"))


def selftest_cases():
    sr = {"next": None, "results": [
        {"id": 0, "title": "کفش ورزشی مردانه", "in_stock": True, "price": 5000000, "discounted_price": 3000000,
         "shop": {"id": 1, "title": "فروشگاه تست", "rating": 4.2, "fast_delivery_city": "تهران", "direct_purchase_enabled": False},
         "promotion_tag": {"title": " ارسال رایگان "}, "flash_sale": True},
        {"id": 0, "title": "کپی همان", "in_stock": True, "price": 1},
        {"id": 1, "title": "ناموجود", "in_stock": False, "price": 100000, "discounted_price": 0, "shop": {"id": 2, "title": "دیگر", "rating": 0}},
        {"id": 2, "title": "بدون قیمت", "in_stock": True, "price": 0}, {"title": "بدون شناسه"}]}
    pv = {"id": 0, "title": "کفش تست", "in_stock": True, "price": 5000000, "discounted_price": 3000000, "shop": {"id": 1, "title": "فروشگاه تست", "rating": 4.2},
          "variations": [{"id": 1, "attributes": [{"name": "سایز", "option": "43"}], "price": 5000000, "discounted_price": 3000000, "stock_quantity": 2},
                         {"id": 2, "attributes": [{"name": "سایز", "option": "44"}], "price": 5000000, "discounted_price": 3000000, "stock_quantity": 0}]}
    sh = {"id": 1, "title": "فروشگاه تست", "rating": 4.1, "surveys_count": 30, "is_verified": True, "followers": 1000, "products_count": 55,
          "fast_delivery_city": "تهران", "direct_purchase_enabled": True, "customer_rating": {"value": 4.5, "count": 9},
          "survey_report": {"customer_satisfaction": 91.4, "positive_high_quality": 80.0, "positive_low_price": 70.5, "positive_timely_delivery": 95.2}}
    ps, po = list(parse_search(sr, "کفش ورزشی", 9)), list(parse_offers(pv, "u"))
    seen, real = [], core.get_json
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, headers, store)) or {"results": [], "variations": [], "title": "x", "id": 1})
    try:
        list(search("کفش ورزشی مردانه", 5))
        list(offers("https://shopino.app/product/77"))
        seller("https://shopino.app/shops/9")
    finally:
        core.get_json = real
    return [
        ("shopino search: price, discount, shop, promo, site-only", ps[0], row(NAME, "کفش ورزشی مردانه", 3000000, "فروشگاه تست", True, f"{SITE}/product/0", match="all", discount=40,
                                                                             shop_id=1, shop_rating=4.2, courier_city="تهران", shop_site_only=True, flash_sale=True, promo="ارسال رایگان")),
        ("shopino search: out of stock has no price, zero rating is None", (ps[1]["toman"], ps[1]["in_stock"], ps[1]["shop_rating"], ps[1]["discount"]), (None, False, None, 0)),
        ("shopino search: no price and duplicate id and missing id", ([r["title"] for r in ps], ps[2]["toman"], ps[2]["in_stock"]), (["کفش ورزشی مردانه", "ناموجود", "بدون قیمت"], None, False)),
        ("shopino search: limit counts unique cards", len(list(parse_search(sr, "x", 1))), 1),
        ("shopino offers: per-size stock, shop on each row", [(r["variant"], r["toman"], r["in_stock"], r["stock"], r["seller"]) for r in po],
         [("سایز: 43", 3000000, True, 2, "فروشگاه تست"), ("سایز: 44", None, False, 0, "فروشگاه تست")]),
        ("shopino offers: no variations falls back to the product", [(r["toman"], r["in_stock"], r["variant"] if "variant" in r else None) for r in parse_offers({**pv, "variations": []}, "u")],
         [(3000000, True, None)]),
        ("shopino seller: ratings, survey percentages, seal", parse_seller(sh),
         {"store": NAME, "seller": "فروشگاه تست", "rating": 4.1, "votes": 30, "since": None, "on_time_pct": 95, "returns_pct": None, "seal": "verified",
          "satisfied_pct": 91, "good_quality_pct": 80, "good_price_pct": 70, "customer_rating": 4.5, "customer_rating_count": 9, "followers": 1000, "products": 55,
          "courier_city": "تهران", "shopino_cart": True, "website": None, "url": f"{SITE}/shops/1"}),
        ("shopino seller: no survey keeps None", (parse_seller({"id": 2, "title": "ت"})["satisfied_pct"], parse_seller({"id": 2, "title": "ت"})["rating"]), (None, None)),
        ("shopino requests are GETs on the app API with pacing on", [(u, s) for u, _, s in seen],
         [(f"{API}/products/search/%DA%A9%D9%81%D8%B4%20%D9%88%D8%B1%D8%B2%D8%B4%DB%8C%20%D9%85%D8%B1%D8%AF%D8%A7%D9%86%D9%87/?page_size=5", NAME),
          (f"{API}/products/77/", NAME), (f"{API}/shops/9/", NAME)]),
        ("shopino ids from urls and refs", (product_id("https://shopino.app/product/3"), product_id("5"), shop_ref("https://shopino.app/shops/489"), shop_ref("shop_sample")),
         (3, 5, "489", "shop_sample")),
        ("shopino match is strict", (match("https://shopino.app/product/1"), match("https://evil.example/shopino.app"), match("http://shopino.app/")), (True, False, False)),
        ("shopino bad refs fail", lambda: product_id("https://shopino.app/"), ValueError),
        ("shopino bad shop ref fails", lambda: shop_ref("a b/c"), ValueError),
        ("shopino search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("shopino offers layout change fails loudly", lambda: list(parse_offers({"title": "x"}, "u")), LayoutChanged),
        ("shopino seller layout change fails loudly", lambda: parse_seller({}), LayoutChanged),
    ]

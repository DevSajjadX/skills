"""SnappMarket (snapp.market): groceries from stores that deliver to a point, one JSON API (`svc.snapp.market`). Prices are Toman.

Snappfood restaurants are not read. Every price depends on the delivery point: `search` takes `at=(lat, lng)`
(`--at`), or `city` as a place name that Snappfood's map search turns into a point; with neither it uses Tehran
(35.6997, 51.3380) and says so on stderr. A search row is one product in one store (`seller` is the store) with the
store's `store_code`, open flag, delivery fee and minimum order (Toman) as extras.

The site's product and store page addresses are not known to this reader, so a row's `url` is a handle it can read
back, `https://snapp.market/?vendorCode=<store>&productId=<id>`, not a verified page. `offers` takes that handle (or
any snapp.market URL carrying both query values) and gives the product's current price in that store. `reviews`
takes a store: a bare store code (`0cccc`), a handle URL, or any snapp.market URL with `vendorCode=<code>` or a
path segment that is the code; it returns the store's 30 most relevant comments (rated 0-10 by the site, shown as
0-5 stars). The reference reads no installment data, so there is no `installments`. Every request is a GET.
"""

from __future__ import annotations

import re
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "snappmarket", "grocery", False
CREDIT = "sepehr071/snapp-mcp (MIT)"
SITE = "https://snapp.market"
API = "https://svc.snapp.market"
MAP = "https://snappfood.ir/map/address/place"  # the geocoder; it wants `lon`, not `long`, and no client params
PARAMS = {"client": "PWA", "deviceType": "PWA", "appVersion": "1.403.1"}
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}
MAP_HEADERS = {"Accept": "application/json", "Origin": "https://snappfood.ir", "Referer": "https://snappfood.ir/"}
CODE = re.compile(r"[0-9a-z]{4,10}")
STORES_PER_PAGE = 12


def match(url):
    return core.host_match(url, "snapp.market")


def api(path, **params):
    q = urlencode({k: v for k, v in {**PARAMS, **params}.items() if v is not None})
    return core.get_json(f"{API}{path}?{q}", HEADERS, store=NAME)


def handle(code, pid):
    return f"{SITE}/?{urlencode({'vendorCode': code, 'productId': pid})}"


def read_handle(url):
    q = parse_qs(urlparse(url).query)
    code, pid = (q.get("vendorCode") or [""])[0], (q.get("productId") or [""])[0]
    if not CODE.fullmatch(code) or not pid.isdigit():
        raise ValueError(f"not a SnappMarket product handle (needs vendorCode and productId): {url}")
    return code, int(pid)


def store_code(ref):
    """A store code from a bare code, a `vendorCode=` query or the last path segment that looks like one."""
    ref = ref.strip()
    if "://" not in ref:
        parts = [ref]
    else:
        u = urlparse(ref)
        parts = [*(parse_qs(u.query).get("vendorCode") or []), *reversed([p for p in u.path.split("/") if p])]
    code = next((p for p in parts if CODE.fullmatch(p)), None)
    if not code:
        raise ValueError(f"not a SnappMarket store code or URL: {ref}")
    return code


def stars(rating):
    """The site rates 0-10 (0 = not rated yet); stars are 0-5."""
    return round(rating / 2, 1) if rating else None


def geocode(place):
    data = core.get_json(f"{MAP}?{urlencode({'place': place, 'lat': core.TEHRAN[0], 'lon': core.TEHRAN[1]})}", MAP_HEADERS, store=NAME)
    item = data[0] if isinstance(data, list) and data else data
    if not isinstance(item, dict) or item.get("status") is False:
        raise LayoutChanged("the map search did not answer with a place list")
    for p in item.get("data") or []:
        loc = p.get("location") or {}
        if "latitude" in loc and "longitude" in loc:
            return float(loc["latitude"]), float(loc["longitude"])
    raise ValueError(f"snappmarket: no place matches {place!r}")


def point(at, city):
    if at:
        return at
    if city:
        return geocode(city)
    print(f"{NAME}: no --at, using Tehran", file=sys.stderr)
    return core.TEHRAN


def product_row(q, store, p, handle_code):
    stock = p.get("stock")
    price = int(p.get("price") or 0)  # Toman already
    discount = int(p.get("discount") or 0)
    final = price - discount
    ok = stock is None or stock > 0
    title = (p.get("title") or "").strip()
    return row(NAME, title, final if ok and final > 0 else None, store.get("title"), None if stock is None else stock > 0,
               handle(handle_code, p["id"]), match=match_level(q, title), brand=p.get("brand") or None,
               discount=core.discount_pct(final, price), stock=stock, store_code=handle_code,
               store_open=store.get("is_open"), store_rating=stars(store.get("rating")),
               delivery_fee=store.get("deliveryFee"), min_order=store.get("minOrder"))


def parse_search(body, q, limit):
    if not body:
        return
    if not isinstance(body, dict) or body.get("status") is False:
        raise LayoutChanged("the search did not answer with a data object")
    vpv = dig(body, "data").get("vendor_product_variations")
    vpv = {} if vpv is None else vpv
    if not isinstance(vpv, dict):
        raise LayoutChanged("data.vendor_product_variations is not an object")
    rows = []
    for v in vpv.get("items") or []:
        if not v.get("code") or not v.get("deliver", True) or not v.get("does_deliver", True):
            continue
        rows += [product_row(q, v, p, v["code"]) for p in v.get("products") or [] if p.get("id") is not None]
    rows.sort(key=lambda r: (r["match"] != "all", r["toman"] is None, r["toman"] or 0))
    yield from rows[:limit]


def parse_offer(body, code, pid):
    d = dig(body, "data", "details", kind=dict)
    price, discount = int(d.get("price") or 0), int(d.get("discount") or 0)  # Toman already
    final = price - discount
    desc = (d.get("description") or "").strip()
    yield row(NAME, (d.get("title") or "").strip(), final if final > 0 else None, None, None, handle(code, pid),
              brand=d.get("brandTitle") or None, category=d.get("categoryTitle"), subcategory=d.get("subcategoryTitle"),
              discount=core.discount_pct(final, price), store_code=code,
              description=desc[:400] or None, badges=[b.get("name") for b in d.get("badges") or [] if b.get("name")])


def parse_reviews(body, url):
    data = dig(body, "data")
    yield {"store": NAME, "url": url, "kind": "summary", "count": data.get("count")}
    for c in dig(data, "comments", kind=list):
        replies = c.get("replies") or []
        yield {"store": NAME, "url": url, "stars": stars(c.get("rating")), "text": (c.get("commentText") or "").strip() or None,
               "date": (c.get("createdDate") or "")[:10] or None, "verified": None, "pros": None, "cons": None,
               "reply": (replies[0].get("commentText") or replies[0].get("text")) if replies and isinstance(replies[0], dict) else None,
               "likes": None, "feeling": c.get("feeling")}


def search(q, limit, *, at=None, city=None, installment=False):
    lat, lng = point(at, city)
    body = api("/mobile/v3/search", query=q.strip(), lat=lat, long=lng, superType="[4]", new_search=1, page=0, size=STORES_PER_PAGE)
    yield from parse_search(body, q, limit)


def offers(url):
    code, pid = read_handle(url)
    yield from parse_offer(api("/express-search/mobile/v2/product-variation/view", productVariationId=pid, vendorCode=code), code, pid)


def reviews(url, limit):
    code = store_code(url)
    body = api("/mobile/v1/restaurant/vendor-comment", vendorCode=code)
    for i, r in enumerate(parse_reviews(body, f"{SITE}/?{urlencode({'vendorCode': code})}")):
        if i > limit:  # the summary row is free, then `limit` comments
            break
        yield r


def selftest_cases():
    sr = {"data": {"vendor_product_variations": {"total_product": 2, "items": [
        {"code": "0aaaa", "title": "سوپر تست", "rating": 9.0, "is_open": True, "deliveryFee": 34000, "minOrder": 100000, "deliver": True,
         "products": [{"id": 0, "title": "شیر کم چرب تست ۱ لیتری", "brand": "برند", "price": 158000, "discount": 8000, "stock": 36},
                      {"id": 1, "title": "شیر پرچرب", "price": 100000, "discount": 0, "stock": 0}]},
        {"code": "0bbbb", "title": "دور", "rating": 0, "is_open": False, "deliveryFee": 1, "minOrder": 2, "deliver": False, "products": [{"id": 2, "title": "شیر کم چرب", "price": 1}]},
        {"title": "بدون کد", "products": [{"id": 3, "title": "x", "price": 1}]}]}}}
    ps = list(parse_search(sr, "شیر کم چرب", 9))
    po = list(parse_offer({"data": {"details": {"id": 0, "title": "محصول نمونه", "brandTitle": "برند", "price": 159000, "discount": 0, "description": "  " + "ن" * 500,
                                                "categoryTitle": "خواربار", "badges": [{"name": "کالابرگ"}]}}}, "0aaaa", 0))
    pr = list(parse_reviews({"data": {"count": 6, "comments": [
        {"createdDate": "2026-01-02 03:04:05", "commentText": " ارسال نشده ", "rating": 2, "feeling": "SAD", "replies": []},
        {"createdDate": None, "commentText": "", "rating": 0, "replies": [{"commentText": "پاسخ"}]}]}}, "u"))
    seen, real, err = [], core.get_json, sys.stderr
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, store)) or (
        [{"status": True, "data": [{"name": "آزادی", "location": {"latitude": "35.7", "longitude": "51.4"}}]}] if "/map/" in url
        else {"data": {"details": {"id": 7}}} if "view" in url else {}))
    try:
        got_at, got_city = point((1.0, 2.0), None), point(None, "آزادی")
        list(search("a b", 3, at=(35.5, 51.2)))
        list(offers(handle("0aaaa", 7)))
    except Exception as e:  # noqa: BLE001 the case below reports it
        got_at = got_city = repr(e)
    finally:
        core.get_json = real
    sys.stderr = io = __import__("io").StringIO()
    try:
        tehran = point(None, None)
    finally:
        sys.stderr = err
    return [
        ("snappmarket search: price after discount, store extras, match, handle url", (ps[0]["toman"], ps[0]["seller"], ps[0]["discount"], ps[0]["match"], ps[0]["store_code"], ps[0]["store_rating"],
                                                                                    ps[0]["delivery_fee"], ps[0]["min_order"], ps[0]["store_open"], ps[0]["url"]),
         (150000, "سوپر تست", 5, "all", "0aaaa", 4.5, 34000, 100000, True, f"{SITE}/?vendorCode=0aaaa&productId=0")),
        ("snappmarket search: out of stock has no price, stays last", (ps[1]["toman"], ps[1]["in_stock"], len(ps)), (None, False, 2)),
        ("snappmarket search: store that does not deliver and store without code are skipped", [r["store_code"] for r in ps], ["0aaaa", "0aaaa"]),
        ("snappmarket search: empty body is no rows", list(parse_search({}, "x", 3)), []),
        ("snappmarket offers: price, brand, description cut, badges", (po[0]["toman"], po[0]["brand"], len(po[0]["description"]), po[0]["badges"]), (159000, "برند", 400, ["کالابرگ"])),
        ("snappmarket reviews: summary, stars from 0-10, no stars when unrated, reply", ([r.get("count") for r in pr[:1]], [(r["stars"], r["text"], r["date"], r["reply"]) for r in pr[1:]]),
         ([6], [(1.0, "ارسال نشده", "2026-01-02", None), (None, None, None, "پاسخ")])),
        ("snappmarket point: --at wins, a city is geocoded, nothing means Tehran and says so", (got_at, got_city, tehran, io.getvalue()),
         ((1.0, 2.0), (35.7, 51.4), core.TEHRAN, "snappmarket: no --at, using Tehran\n")),
        ("snappmarket requests are GETs with the store name, the point and client params", [(u.split("?")[0], s) for u, s in seen],
         [(MAP, NAME), (f"{API}/mobile/v3/search", NAME), (f"{API}/express-search/mobile/v2/product-variation/view", NAME)]),
        ("snappmarket store refs", (store_code("0cccc"), store_code(f"{SITE}/?vendorCode=0aaaa"), store_code("https://snapp.market/store/0bbbb/")), ("0cccc", "0aaaa", "0bbbb")),
        ("snappmarket handle round trip", read_handle(handle("0aaaa", 5)), ("0aaaa", 5)),
        ("snappmarket match is strict", (match("https://snapp.market/x"), match("https://evil.example/snapp.market"), match("http://snapp.market/")), (True, False, False)),
        ("snappmarket bad store ref fails", lambda: store_code("https://snapp.market/"), ValueError),
        ("snappmarket handle without a product fails", lambda: read_handle(f"{SITE}/?vendorCode=0aaaa"), ValueError),
        ("snappmarket search layout change fails loudly", lambda: list(parse_search({"data": {"vendor_product_variations": []}}, "q", 9)), LayoutChanged),
        ("snappmarket offers layout change fails loudly", lambda: list(parse_offer({"data": {}}, "0aaaa", 0)), LayoutChanged),
        ("snappmarket reviews layout change fails loudly", lambda: list(parse_reviews({"data": {"count": 0}}, "u")), LayoutChanged),
    ]

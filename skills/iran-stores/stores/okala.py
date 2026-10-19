"""Okala (okala.com): groceries from stores that deliver to a point, one JSON gateway (`apigateway.okala.com/api`). The API speaks
Rial; every price here is Toman.

Everything is read as a guest: nothing logs in, reads an account or sends a write request. Okala's own text search needs a
login, so `search` does the guest thing the site allows: it matches the query words against the category names near the
point (category names, not brands or product names, so "شیر کم چرب" finds the milk category) and lists that category's
products from every open store that delivers there. Each row's `match` says how many query words the product title has.

Location: `search` takes `at=(lat, lng)` (`--at`), or `city` as a place name that Okala's map search (ParsiMap, biased to
Tehran) turns into a point; with neither it raises ValueError (no Okala store delivers to a default point, so there is
no fallback). Pass `--at` with a point inside a delivery area, e.g. Azadi Square, 35.6997,51.3380. `offers` gives the product's price in the store its URL
names (`/product/<id>?storeId=<store>`), plus other stores selling the same product in that category around that store
when the category listing shows it (the listing holds at most 12 products per store, so the list can be short).
`seller` and the store lookup behind `offers` ask from Tehran, which only changes coverage flags, not store data.
`reviews` and `seller` take a store (`https://www.okala.com/store/<id>` or a bare id). Reviewer names are not copied.
There is no installment data. Every request is a GET.
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "okala", "grocery", False
CREDIT = "sepehr071/okala-mcp (MIT)"
SITE = "https://www.okala.com"
API = "https://apigateway.okala.com/api"
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/", "source": "okala", "ui-version": "2.0"}
MAX_REVIEWS = 50  # the API's page size cap in the reference


def match(url):
    return core.host_match(url, "okala.com")


def user_id():
    """One `x-user-unique-id` per machine, created once beside the pacing state, so Okala sees a stable client."""
    path = core.state_path(NAME).with_suffix(".id")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(uuid.uuid4()), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def api(path, **params):
    q = urlencode({k: v for k, v in params.items() if v is not None})
    body = core.get_json(f"{API}{path}" + (f"?{q}" if q else ""), {**HEADERS, "x-user-unique-id": user_id()}, store=NAME)
    if isinstance(body, dict) and (body.get("success") is False or body.get("isSuccess") is False):
        # The unicorn lists answer HTTP 200 with success false for an unknown slug, store or point.
        tags = {t.get("key") for t in body.get("tags") or [] if isinstance(t, dict)}
        why = body.get("errorMessage") or body.get("message") or ("no Okala store delivers to this point" if "stores" in tags else "unknown id or slug, or nothing near this point")
        raise ValueError(f"okala.com found nothing for this request: {str(why)[:200]}")
    return body


def product_url(pid, sid):
    return f"{SITE}/product/{pid}?storeId={sid}"


def ids_of(url):
    """(product id, store id or None) from /product/<id>?storeId=<n>."""
    u = urlparse(url)
    m = re.search(r"/product/(\d{1,10})", u.path)
    if not m:
        raise ValueError(f"not an Okala product URL: {url}")
    sid = (parse_qs(u.query).get("storeId") or [""])[0]
    return int(m.group(1)), int(sid) if sid.isdigit() else None


def store_id(ref):
    m = re.search(r"/store/(\d{1,10})", ref) or re.fullmatch(r"\s*(\d{1,10})\s*", ref)
    if not m:
        raise ValueError(f"not an Okala store URL or id: {ref}")
    return int(m.group(1))


def fee(rial):
    return int(rial or 0) // 10  # a fee of 0 stays 0 (free)


def badges(raw):
    """`catalogBadges` is JSON text: '[{"name": "kalabarg"}]' (kalabarg is the government voucher)."""
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return []
    return [b["name"] for b in items or [] if isinstance(b, dict) and b.get("name")]


def pid_of(p):
    return p["id"] if p.get("id") is not None else p.get("productId")


def stocked(p):
    return bool(p.get("hasQuantity", (p.get("quantity") or 0) > 0)) and p.get("supplyStatus") != 2  # 2: the store does not sell it


def product_row(q, p, sid, store_name):
    price, final = core.rial_to_toman(p.get("price")), core.rial_to_toman(p.get("okPrice"))
    pct = int(p.get("discountPercent") or 0)
    ok = stocked(p) and final is not None
    title = (p.get("name") or "").strip()
    return row(NAME, title, final if ok else None, store_name, stocked(p), product_url(pid_of(p), sid),
               match=match_level(q, title), discount=pct, list_price=price if pct else None, store_id=sid,
               max_order=p.get("maxOrderLimit"), badges=badges(p.get("catalogBadges")) or None)


def closed(store):
    return bool((store.get("earliestSlot") or {}).get("isClosed"))


def groups(body, q):
    """Rows of a products/nearby reply: one group per open store."""
    for g in dig(body, "data", kind=list):
        store = g.get("store") or {}
        if closed(store):
            continue
        for p in g.get("products") or []:
            if pid_of(p) is not None:
                yield product_row(q, p, store.get("storeId"), store.get("storeName"))


def flat(nodes, seen=None):
    seen = {} if seen is None else seen
    for n in nodes:
        seen.setdefault(n["id"], n)  # a node can sit under several parents
        flat(n.get("children") or [], seen)
    return seen


def best_categories(tree, q):
    """The category names that hold the most query words (at most 2 that tie for the best)."""
    words = [w for w in q.split() if len(w) > 1 or w.isdigit()]
    scored = [(sum(match_level(w, n.get("name") or "") == "all" for w in words), n) for n in flat(tree).values() if n.get("latinName")]
    scored = sorted(((s, n) for s, n in scored if s), key=lambda t: (-t[0], len(t[1].get("name") or ""), t[1].get("level") or 0))
    return [n for s, n in scored if scored and s == scored[0][0]][:2]


def parse_search(tree, replies, q, limit):
    """`tree` is the category list, `replies` maps each used slug's products/nearby reply (see `search`)."""
    rows = {}
    for body in replies:
        for r in groups(body, q):
            rows.setdefault(r["url"], r)
    out = sorted(rows.values(), key=lambda r: (r["match"] != "all", r["match"] == "none", not r["in_stock"], r["toman"] is None, r["toman"] or 0))
    yield from out[:limit]


def parse_offers(pdp, others, url):
    pid, _ = ids_of(url)
    sid = dig(pdp, "storeId")
    title = (dig(pdp, "name") or "").strip()
    price, final = core.rial_to_toman(pdp.get("price")), core.rial_to_toman(pdp.get("okPrice"))
    pct = int(pdp.get("discountPercent") or 0)
    ok = stocked(pdp) and final is not None
    desc = (pdp.get("description") or "").strip()
    common = {"brand": pdp.get("brandName"), "category": pdp.get("categoryName"), "store_id": sid}
    yield row(NAME, title, final if ok else None, pdp.get("storeName"), stocked(pdp), product_url(pid, sid), discount=pct,
              list_price=price if pct else None, sold_here=pdp.get("supplyStatus") != 2, quantity=pdp.get("quantity"),
              description=desc[:400] if desc and desc != title else None, **common)
    for r in others:
        if r["store_id"] != sid and r["url"].startswith(f"{SITE}/product/{pid}?"):
            yield {**{k: v for k, v in r.items() if k != "match"}, **{k: v for k, v in common.items() if k != "store_id"}}  # no query here, so no match


def parse_reviews(body, sid):
    data = dig(body, "data")
    url = f"{SITE}/store/{sid}"
    yield {"store": NAME, "url": url, "kind": "summary", "count": data.get("totalCount") or 0}
    for r in dig(data, "items", kind=list):
        reasons = lambda kind: [x.get("title") for x in r.get("reasons") or [] if x.get("reasonType") == kind and x.get("title")] or None  # noqa: E731
        yield {"store": NAME, "url": url, "stars": r.get("vendorRate") or None, "text": (r.get("comment") or "").strip() or None,
               "date": (r.get("submittedAt") or "")[:10] or None, "verified": None, "pros": reasons("Like"), "cons": reasons("Dislike"),
               "reply": None, "likes": None}


def parse_seller(d, reviews_total, sid):
    if not d.get("isExist") and not d.get("storeName"):
        raise ValueError(f"okala.com has no store {sid}; check the id")
    return {"store": NAME, "seller": dig(d, "storeName"), "rating": d.get("rate") or None, "votes": d.get("csatCount") or 0, "since": None,
            "on_time_pct": None, "returns_pct": None, "seal": None, "review_count": reviews_total, "type": d.get("storeCategoryName") or d.get("storeType"),
            "minimum_order": fee(d.get("minimumOrder")), "address": d.get("storeAddress"), "status": d.get("storeStatusMessage"),
            "labels": [x.get("title") for x in d.get("storeLabels") or [] if x.get("title")], "url": f"{SITE}/store/{sid}"}


def geocode(place):
    body = api("/parsimap/forward", searchText=place, district="تهران", onlyInDistrict="false")
    results = (body.get("results") or []) if isinstance(body, dict) and body.get("status") == "OK" else []  # ParsiMap answers HTTP 200 always
    for r in results:
        c = (r.get("geo_location") or {}).get("center") or {}
        if "lat" in c and "lng" in c:
            return float(c["lat"]), float(c["lng"])
    raise ValueError(f"okala: no place matches {place!r}")


def point(at, city):
    if at:
        return at
    if city:
        return geocode(city)
    raise ValueError("okala needs --at LAT,LNG or --city")


def nearby_products(slug, lat, lng):
    return api("/unicorn/v2/products/nearby", slug=slug, lat=lat, lon=lng)


def search(q, limit, *, at=None, city=None, installment=False):
    lat, lng = point(at, city)
    tree = dig(api("/unicorn/v3/categories/nearby", lat=lat, lon=lng), "data", "categories", kind=list)
    used = best_categories(tree, q)
    if not used:
        return
    yield from parse_search(tree, [nearby_products(n["latinName"], lat, lng) for n in used], q, limit)


def offers(url):
    pid, sid = ids_of(url)
    if sid is None:
        raise ValueError(f"the Okala product URL needs ?storeId=<store>: {url}")
    pdp = api("/Unicorn/v1/catalog/pdp", sId=sid, pId=pid)
    if not isinstance(pdp, dict) or not pdp.get("name"):
        raise ValueError(f"okala.com has no product {pid} in store {sid}")
    slug = ((pdp.get("categoryWebLink") or "").rstrip("/").rsplit("/", 1)[-1]) or None
    others = []
    if slug:
        try:
            d = dig(store_details(sid), "data", kind=dict)
            if d.get("storeLat") is not None and d.get("storeLng") is not None:  # the stores around this store, not around a default point
                others = list(groups(nearby_products(slug, d["storeLat"], d["storeLng"]), ""))
        except ValueError as e:
            print(f"{NAME}: offers: no other stores listed ({e})", file=sys.stderr)
    yield from parse_offers(pdp, others, url)


def store_details(sid):
    return api("/opex/v2/stores/details", Latitude=core.TEHRAN[0], longitude=core.TEHRAN[1], StoreId=sid, customerSegments="null")


def reviews(url, limit):
    sid = store_id(url)
    yield from parse_reviews(api(f"/review/v1/stores/{sid}/reviews", PageIndex=1, PageSize=max(1, min(limit, MAX_REVIEWS)), Sort="Newest"), sid)


def seller(ref):
    sid = store_id(ref)
    d = dig(store_details(sid), "data", kind=dict)
    total = dig(api(f"/review/v1/stores/{sid}/reviews", PageIndex=1, PageSize=1), "data").get("totalCount") or 0
    return parse_seller(d, total, sid)


@contextlib.contextmanager
def fresh_cache():
    from unittest import mock
    with tempfile.TemporaryDirectory() as d, mock.patch.object(core, "CACHE_DIR", Path(d)):
        yield


def selftest_cases():
    tree = [{"id": 1, "name": "لبنیات", "latinName": "dairy", "level": 1, "children": [
        {"id": 2, "name": "شیر", "latinName": "milk", "level": 2, "children": []},
        {"id": 3, "name": "شیر کم چرب", "latinName": "low-fat-milk", "level": 3}]},
        {"id": 2, "name": "شیر", "latinName": "milk", "level": 1}, {"id": 5, "name": "شیرینی", "latinName": "sweets", "level": 1}, {"id": 4, "name": "بدون اسلاگ"}]
    prod = lambda i, **kw: {"id": i, "name": f"شیر کم چرب تست {i}", "okPrice": 1580000, "price": 1600000, "discountPercent": 1, "hasQuantity": True, "supplyStatus": 1,  # noqa: E731
                            "maxOrderLimit": 6, "catalogBadges": '[{"name": "kalabarg"}]', **kw}
    body = {"data": [{"store": {"storeId": 0, "storeName": "فروشگاه تست", "earliestSlot": {"isClosed": False}}, "products": [prod(0), prod(1, okPrice=0, hasQuantity=False), prod(2, supplyStatus=2), {"name": "بدون شناسه"}]},
                     {"store": {"storeId": 1, "storeName": "بسته", "earliestSlot": {"isClosed": True}}, "products": [prod(0)]}]}
    ps = list(parse_search(tree, [body, body], "شیر کم چرب", 9))
    pdp = {"storeId": 0, "storeName": "فروشگاه تست", "name": "شیر تست", "okPrice": 1580000, "price": 1600000, "discountPercent": 1, "hasQuantity": True, "quantity": 5,
           "supplyStatus": 1, "brandName": "برند", "categoryName": "لبنیات", "description": "شیر تست"}
    other = [{**product_row("", prod(0), 1, "دومی"), "store_id": 1}, {**product_row("", prod(9), 1, "دیگر"), "store_id": 1}]
    po = list(parse_offers(pdp, other, "https://www.okala.com/product/0?storeId=0"))
    rv = list(parse_reviews({"data": {"totalCount": 4, "items": [
        {"vendorRate": 5, "comment": " عالی ", "submittedAt": "2026-10-03T10:00:00Z", "reviewerName": "نام", "hasName": True,
         "reasons": [{"title": "تنوع", "reasonType": "Like"}, {"title": "تاریخ", "reasonType": "Dislike"}]},
        {"vendorRate": 0, "comment": "", "submittedAt": None, "reasons": []}]}}, 0))
    sl = parse_seller({"isExist": True, "storeName": "فروشگاه تست", "rate": 4.5, "csatCount": 10, "storeCategoryName": "سوپرمارکت", "minimumOrder": 1000000,
                       "storeLabels": [{"title": "تازه"}]}, 7, 0)
    seen, real, err = [], core.get_json, sys.stderr

    def fake(url, headers=None, store=None):
        seen.append((url.split("?")[0].removeprefix(API), store))
        return {"data": {"categories": tree}} if "categories" in url else {"status": "OK", "results": [{"geo_location": {"center": {"lat": 35.7, "lng": 51.4}}}]} if "parsimap" in url else \
            body if "products/nearby" in url else {"data": {"totalCount": 0, "items": []}} if "reviews" in url else {"data": {"storeName": "x", "storeLat": 35.7, "storeLng": 51.4}} if "details" in url else {**pdp, "categoryWebLink": "/c/milk"}
    core.get_json = fake
    sys.stderr = __import__("io").StringIO()
    try:
        with fresh_cache():
            got_city = point(None, "آزادی")
            list(search("شیر", 3, at=(35.5, 51.2)))
            list(offers("https://www.okala.com/product/0?storeId=0"))
            list(reviews("https://www.okala.com/store/5", 500))
            seller("5")
            first_id = user_id()
            stable = (first_id == user_id(), core.state_path(NAME).with_suffix(".id").read_text() == first_id, len(first_id))
    finally:
        core.get_json, sys.stderr = real, err

    def offers_without_others():
        def fake2(url, headers=None, store=None):
            if "products/nearby" in url:
                raise ValueError("nothing here")
            return fake(url, headers, store)
        core.get_json, sys.stderr = fake2, __import__("io").StringIO()
        try:
            with fresh_cache():
                rows = list(offers("https://www.okala.com/product/0?storeId=0"))
            return len(rows), sys.stderr.getvalue()
        finally:
            core.get_json, sys.stderr = real, err

    def failing():
        core.get_json = lambda *a, **k: {"success": False, "tags": [{"key": "stores"}]}
        try:
            with fresh_cache():
                api("/x")
        finally:
            core.get_json = real
    return [
        ("okala search: price in Toman, discount, list price, badges, match, url", (ps[0]["toman"], ps[0]["discount"], ps[0]["list_price"], ps[0]["badges"], ps[0]["match"], ps[0]["seller"], ps[0]["url"]),
         (158000, 1, 160000, ["kalabarg"], "all", "فروشگاه تست", f"{SITE}/product/0?storeId=0")),
        ("okala search: out of stock and not sold have no price, closed store and id-less card skipped, duplicates merged", [(r["url"][-11:], r["toman"], r["in_stock"]) for r in ps],
         [("0?storeId=0", 158000, True), ("1?storeId=0", None, False), ("2?storeId=0", None, False)]),
        ("okala category match: best name wins, a tie takes two, no slug skipped", ([n["latinName"] for n in best_categories(tree, "شیر کم چرب")], [n["latinName"] for n in best_categories(tree, "شیر")], best_categories(tree, "x")),
         (["low-fat-milk"], ["milk", "low-fat-milk"], [])),
        ("okala offers: this store's price first, then only other stores with the same product", [(r["seller"], r["toman"], r["store_id"], r["brand"]) for r in po],
         [("فروشگاه تست", 158000, 0, "برند"), ("دومی", 158000, 1, "برند")]),
        ("okala offers: description equal to the title is dropped", po[0]["description"], None),
        ("okala reviews: summary, stars, date, liked as pros, disliked as cons, no reviewer name", (rv[0]["count"], [(r["stars"], r["text"], r["date"], r["pros"], r["cons"]) for r in rv[1:]], any("reviewer" in str(r) or "نام" in str(r) for r in rv)),
         (4, [(5, "عالی", "2026-10-03", ["تنوع"], ["تاریخ"]), (None, None, None, None, None)], False)),
        ("okala seller: rating, votes, minimum order in Toman, reviews, labels", (sl["seller"], sl["rating"], sl["votes"], sl["minimum_order"], sl["review_count"], sl["labels"], sl["url"]),
         ("فروشگاه تست", 4.5, 10, 100000, 7, ["تازه"], f"{SITE}/store/0")),
        ("okala point: --at wins, a place is geocoded", (point((1.0, 2.0), "آزادی"), got_city), ((1.0, 2.0), (35.7, 51.4))),
        ("okala point: neither --at nor a city is an error, not a Tehran guess", lambda: point(None, None), ValueError),
        ("okala search: neither --at nor a city is an error", lambda: list(search("شیر", 3)), ValueError),
        ("okala category match: whole words only, شیر does not pick the sweets category", [n["latinName"] for n in best_categories(tree, "شیر")], ["milk", "low-fat-milk"]),
        ("okala requests are GETs with the store name, and never a login path", ([p for p, _ in seen], {s for _, s in seen}, any("login" in p.lower() for p, _ in seen)),
         (["/parsimap/forward", "/unicorn/v3/categories/nearby", "/unicorn/v2/products/nearby", "/unicorn/v2/products/nearby", "/Unicorn/v1/catalog/pdp", "/opex/v2/stores/details", "/unicorn/v2/products/nearby", "/review/v1/stores/5/reviews", "/opex/v2/stores/details", "/review/v1/stores/5/reviews"], {NAME}, False)),
        ("okala: one x-user-unique-id is created once and reused, kept in the cache dir", stable, (True, True, 36)),
        ("okala ids from urls", (ids_of("https://www.okala.com/product/2?storeId=3"), ids_of("https://www.okala.com/product/1"), store_id("https://www.okala.com/store/3"), store_id("12")),
         ((2, 3), (1, None), 3, 12)),
        ("okala match is strict", (match("https://www.okala.com/store/1"), match("https://evil.example/okala.com"), match("http://okala.com/")), (True, False, False)),
        ("okala bad refs fail", lambda: store_id("https://www.okala.com/"), ValueError),
        ("okala offers needs a store", lambda: list(offers("https://www.okala.com/product/1")), ValueError),
        ("okala offers: a failed other-stores lookup keeps the product row and says why on stderr", offers_without_others(), (1, "okala: offers: no other stores listed (nothing here)\n")),
        ("okala unknown store is an error", lambda: parse_seller({}, 0, 9), ValueError),
        ("okala success false is an error", failing, ValueError),
        ("okala search layout change fails loudly", lambda: list(parse_search(tree, [{}], "q", 9)), LayoutChanged),
        ("okala offers layout change fails loudly", lambda: list(parse_offers({}, [], "https://www.okala.com/product/1?storeId=0")), LayoutChanged),
        ("okala reviews layout change fails loudly", lambda: list(parse_reviews({"data": {"totalCount": 0}}, 0)), LayoutChanged),
    ]

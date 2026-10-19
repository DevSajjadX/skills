"""Torob (torob.com): JSON API behind a bot check. Prices are Toman already; 0 means no shop has it.

The block trips at about 6 to 10 /v4 calls in a few minutes (reference measurement), so calls are
5 s apart and one 490 pauses every run on this machine for 30 minutes. No proxy, browser or retry after it.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

import iran_stores as core
from iran_stores import LayoutChanged, dig, jalali_to_iso, match_level, number, row

NAME, KIND, DEFAULT = "torob", "general", True
INSTALLMENT_FILTER = True  # `search(installment=True)` sends Torob Pay: only products sold in installments
CREDIT = "sepehr071/torob-mcp (MIT), endpoints re-implemented"
PACE = (5, 1800)
API, SITE, SOURCE = "https://api.torob.com", "https://torob.com", "next_desktop"
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def match(url):
    return core.host_match(url, "torob.com")


def api(path, params, city=None):
    headers = {**HEADERS, **({"Cookie": f"deliver_city={city}"} if city else {})}  # the site filters sellers by this cookie
    return core.get_json(f"{API}{path}?" + urlencode({k: v for k, v in params.items() if v is not None}), headers, store=NAME)


def prk(url):
    if m := UUID.search(url):
        return m.group().lower()
    raise ValueError(f"not a Torob product URL or id: {url}")


def product_url(key):
    return f"{SITE}/p/{key}/"


def city_id(city):
    """A city id, or a Persian name looked up via /v4/city/list/ (exact match first). One extra call for a name."""
    if city is None or str(city).strip().isdigit():
        return int(city) if city is not None else None
    data = api("/v4/city/list/", {"search": str(city).strip(), "size": 10})
    rows = [r for r in (data.get("results") if isinstance(data, dict) else data) or [] if isinstance(r, dict) and r.get("id")]
    if not rows:
        raise ValueError(f"no Torob city matches {city!r}")
    return int(next((r for r in rows if match_level(city, r.get("name")) == "all" and match_level(r.get("name"), city) == "all"), rows[0])["id"])


def price(v):
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def sellers_text(shop_text):
    text = re.sub(r"^در\s+", "", shop_text or "").strip()  # "در ۵ فروشگاه" = "in 5 shops"
    m = re.fullmatch(r"(\S+)\s+فروشگاه", text)
    return f"{number(m.group(1))} sellers" if m and number(m.group(1)) else text or None


def parse_search(data, q, limit):
    for p in dig(data, "results", kind=list)[:limit]:
        parts = (p.get("web_client_absolute_url") or "").split("/")  # "/p/<prk>/<slug>/"
        key = p.get("random_key") or (parts[2] if len(parts) > 2 else None)
        if not key:
            continue
        yield row("torob", p.get("name1"), price(p.get("price")), sellers_text(p.get("shop_text")), bool(price(p.get("price"))),
                  product_url(key), match=match_level(q, f"{p.get('name1') or ''} {p.get('name2') or ''}"), ad=bool(p.get("is_adv")))


def installment_text(v):
    if isinstance(v, dict):
        return v.get("text") or v.get("title") or v.get("description") or None
    return v if isinstance(v, str) and v else None


def parse_offers(data, url):
    for o in dig(data, "results", kind=list):
        p = price(o.get("price")) if o.get("availability") is not False else None  # an unavailable offer has no usable price
        yield row("torob", o.get("name1"), p, o.get("shop_name"), p is not None, url, city=o.get("shop_name2"),
                  updated=(o.get("last_price_change_date") or "").translate(core.DIGITS) or None, ad=bool(o.get("is_adv")),
                  unreliable=bool(o.get("is_price_unreliable")), rating=o.get("shop_score"),
                  rating_count=o.get("shop_votes_count"),
                  warranty="گارانتی ترب" if (o.get("guarantee_info") or {}).get("status") == "enabled" else None,
                  installment=bool(o.get("installment")))


def parse_installments(data, url):
    for o in dig(data, "results", kind=list):
        if o.get("installment") and o.get("availability") is not False:
            yield {"store": NAME, "url": url, "provider": o.get("shop_name"), "months": None, "monthly_toman": None,
                   "total_toman": price(o.get("price")), "down_toman": None,
                   "note": installment_text(o.get("installment")) or "installment offered; terms on the shop's page"}


def chart_series(chart):
    """{'min'|'avg': {label index: Toman}}; series are sparse, joined to the labels on `i`."""
    sets = {}
    for s in dig(chart, "dataSets", kind=list):
        label = str(s.get("label"))
        name = "min" if "کمترین" in label else "avg" if "میانگین" in label else None
        if not name:
            raise LayoutChanged(f"unknown price-chart series {label!r}")
        sets[name] = {int(e["i"]): int(e["val"]) for e in s.get("entries") or [] if price(e.get("val")) and "i" in e}
    return sets


def parse_history(chart, url):
    labels, sets = dig(chart, "labels", kind=list), chart_series(chart)
    for kind in ("min", "avg"):
        for i, val in sorted(sets.get(kind, {}).items()):
            if i < len(labels):
                yield {"store": NAME, "url": url, "date": jalali_to_iso(labels[i]) or labels[i], "toman": val, "kind": kind, "variant": None}


def parse_seller(d):
    if not isinstance(d, dict) or not d.get("id"):
        raise LayoutChanged("shop details without an id")
    lic = [x.get("title") for x in d.get("licenses") or [] if isinstance(x, dict) and x.get("title")]
    seal = {"level": d.get("enamad_level"), "expires": d.get("enamad_expire_date"), "licenses": lic}
    ups, downs = d.get("upvotes"), d.get("downvotes")
    return {"store": NAME, "seller": d.get("name"), "rating": d.get("shop_score"),
            "votes": ups + downs if isinstance(ups, int) and isinstance(downs, int) else None, "upvotes": ups, "downvotes": downs,
            "since": d.get("date_added"), "on_torob": d.get("active_time"), "on_time_pct": None, "returns_pct": None,
            "seal": seal if any(seal.values()) else None, "city": d.get("city"), "province": d.get("province"),
            "torob_warranty": (d.get("guarantee_info") or {}).get("status") == "enabled",
            "website": f"{d.get('url_prefix') or 'https://'}{d['domain']}" if d.get("domain") else None, "url": f"{SITE}/shop/{d['id']}"}


def parse_nearby(data, url):
    raw = next((data[k] for k in ("result", "results") if isinstance(data, dict) and isinstance(data.get(k), list)), None)
    if raw is None:
        raise LayoutChanged("map sellers without result or results")
    for r in raw:
        t = (r.get("working_hours") or {}).get("title") or {}
        p = price(r.get("price"))
        # the endpoint does not name the product, so title stays None; the address is the shop's
        yield row("torob", None, p, r.get("shop_name"), p is not None, url, city=r.get("shop_name2"), address=r.get("name1"),
                  hours=f"{t.get('status') or ''} {t.get('text') or ''}".strip().translate(core.DIGITS) or None, open_now=r.get("is_open"),
                  updated=(r.get("last_price_change_date") or "").translate(core.DIGITS) or None, unreliable=bool(r.get("is_price_unreliable")), note=r.get("name2") or None)


def search(q, limit, *, at=None, city=None, installment=False):
    cid = city_id(city)
    params = {"q": q, "query": q, "page": 0, "size": limit, "source": SOURCE, "cities": cid,
              "torobpay": "true" if installment else None}  # Torob Pay: only products sold in installments
    yield from parse_search(api("/v4/base-product/search/", params, cid), q, limit)


def sellers(url, list_type="products_info", city=None):
    return api("/v4/base-product/sellers/", {"prk": prk(url), "list_type": list_type}, city)


def offers(url):
    yield from parse_offers(sellers(url), url)


def history(url):
    yield from parse_history(api("/v4/base-product/price-chart/", {"prk": prk(url)}), url)


def seller(ref):
    m = re.search(r"/shop/(\d+)", ref) or re.fullmatch(r"(\d+)", ref.strip())
    if not m:
        raise ValueError(f"not a Torob shop URL or id: {ref}")
    return parse_seller(api("/v4/internet-shop/details/", {"id": m.group(1)}))


def installments(url):
    yield from parse_installments(sellers(url), url)


def nearby(url, city):
    cid = city_id(city)
    yield from parse_nearby(api("/v4/base-product/map/sellers/", {"prk": prk(url)}, cid), url)


def torob_search_urls():
    """Whether the search request carries torobpay=true, without and with installment=True."""
    seen, real = [], core.get_json
    core.get_json = lambda url, headers=None, store=None: (seen.append(url) or {"results": []})
    try:
        for inst in (False, True):
            list(search("q", 5, installment=inst))
    finally:
        core.get_json = real
    return tuple("torobpay=true" in u for u in seen)


def selftest_cases():
    tr = {"results": [{"name1": "محصول نمونه", "price": 10000000, "shop_text": "در ۳۰ فروشگاه",
                       "web_client_absolute_url": "/p/00000000-0000-0000-0000-000000000001/slug/"},
                      {"name1": "محصول دیگر", "price": 0, "shop_text": "در فروشگاه دیگر", "random_key": "00000000-0000-0000-0000-000000000002"},
                      {"name1": "آگهی نمونه", "price": 5, "is_adv": True, "random_key": "00000000-0000-0000-0000-000000000003"},
                      {"name1": "no key", "price": 1}]}
    sl = {"results": [
        {"name1": "محصول نمونه", "price": 20000000, "availability": True, "shop_name": "فروشگاه نمونه", "shop_name2": "تهران",
         "is_adv": True, "last_price_change_date": "۷ روز پیش", "shop_score": 4.5, "shop_votes_count": 10,
         "is_price_unreliable": False, "guarantee_info": {"status": "enabled"}, "installment": {"text": "قسطی"}},
        {"name1": "محصول نمونه", "price": 100, "availability": False, "shop_name": "ناموجود", "is_price_unreliable": True,
         "guarantee_info": {"status": "disabled"}, "installment": None}]}
    chart = {"labels": ["۱۱ مهر ۱۴۰۵", "۱۸ مهر ۱۴۰۵"], "dataSets": [
        {"label": "میانگین قیمت", "entries": [{"val": 30000000, "i": 0}, {"val": 25000000, "i": 1}]},
        {"label": "کمترین قیمت", "entries": [{"val": 15000000, "i": 1}, {"val": 0, "i": 0}]}]}
    shop = {"id": 1, "name": "فروشگاه", "shop_score": 4, "upvotes": 8, "downvotes": 2, "date_added": "۱۴۰۰", "active_time": "۵ سال",
            "enamad_level": 3, "licenses": [{"title": "نماد"}], "city": "تهران", "domain": "example.com"}
    mp = {"result": [{"shop_name": "فروشگاه", "shop_name2": "تهران", "name1": "خیابان یک", "price": 5, "is_open": True,
                      "working_hours": {"title": {"status": "باز", "text": "تا ۲۱:۰۰"}}, "last_price_change_date": "۱ روز پیش"},
                     {"shop_name": "بدون قیمت", "price": 0}]}
    trs, tro = list(parse_search(tr, "نمونه", 9)), list(parse_offers(sl, "u"))
    hist = list(parse_history(chart, "u"))
    return [
        ("torob shop count, match, ad flag", trs[0], row("torob", "محصول نمونه", 10000000, "30 sellers", True,
                                                         "https://torob.com/p/00000000-0000-0000-0000-000000000001/", match="all", ad=False)),
        ("torob zero price is unavailable", (trs[1]["toman"], trs[1]["in_stock"], trs[1]["seller"], trs[1]["match"]), (None, False, "فروشگاه دیگر", "none")),
        ("torob sponsored slot carries ad", trs[2]["ad"], True),
        ("torob result without a product key is skipped", len(trs), 3),
        ("torob offers: trust, warranty, installment, updated", tro[0], row(
            "torob", "محصول نمونه", 20000000, "فروشگاه نمونه", True, "u", city="تهران", updated="7 روز پیش", ad=True, unreliable=False,
            rating=4.5, rating_count=10, warranty="گارانتی ترب", installment=True)),
        ("torob offers: unavailable offer has no price, flagged unreliable", (tro[1]["toman"], tro[1]["in_stock"], tro[1]["unreliable"]), (None, False, True)),
        ("torob installments only from buyable installment offers", list(parse_installments(sl, "u")), [
            {"store": "torob", "url": "u", "provider": "فروشگاه نمونه", "months": None, "monthly_toman": None,
             "total_toman": 20000000, "down_toman": None, "note": "قسطی"}]),
        ("torob history joins sparse series on index, zero is skipped", [(h["date"], h["kind"], h["toman"]) for h in hist],
         [("2026-10-10", "min", 15000000), ("2026-10-03", "avg", 30000000), ("2026-10-10", "avg", 25000000)]),
        ("torob seller", parse_seller(shop), {
            "store": "torob", "seller": "فروشگاه", "rating": 4, "votes": 10, "upvotes": 8, "downvotes": 2, "since": "۱۴۰۰",
            "on_torob": "۵ سال", "on_time_pct": None, "returns_pct": None,
            "seal": {"level": 3, "expires": None, "licenses": ["نماد"]}, "city": "تهران", "province": None, "torob_warranty": False,
            "website": "https://example.com", "url": "https://torob.com/shop/1"}),
        ("torob nearby", list(parse_nearby(mp, "u")), [
            row("torob", None, 5, "فروشگاه", True, "u", city="تهران", address="خیابان یک", hours="باز تا 21:00", open_now=True,
                updated="1 روز پیش", unreliable=False, note=None),
            row("torob", None, None, "بدون قیمت", False, "u", city=None, address=None, hours=None, open_now=None,
                updated=None, unreliable=False, note=None)]),
        ("torob product id from a URL", prk("https://torob.com/p/00000000-0000-0000-0000-000000000001/slug/"), "00000000-0000-0000-0000-000000000001"),
        ("torob match is strict", (match("https://torob.com/p/x"), match("https://evil.example/torob.com"), match("http://torob.com/")), (True, False, False)),
        ("torob pace is gap 5, cooldown 1800", PACE, (5, 1800)),
        ("torob non-product URL fails", lambda: prk("https://torob.com/"), ValueError),
        ("torob search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("torob offers layout change fails loudly", lambda: list(parse_offers({"results": {}}, "u")), LayoutChanged),
        ("torob installments layout change fails loudly", lambda: list(parse_installments({}, "u")), LayoutChanged),
        ("torob history: an unknown series label fails loudly", lambda: list(parse_history({"labels": ["x"], "dataSets": [{"label": "؟", "entries": []}]}, "u")), LayoutChanged),
        ("torob history layout change fails loudly", lambda: list(parse_history({"labels": []}, "u")), LayoutChanged),
        ("torob seller layout change fails loudly", lambda: parse_seller({}), LayoutChanged),
        ("torob nearby layout change fails loudly", lambda: list(parse_nearby({}, "u")), LayoutChanged),
        ("torob search sends torobpay only for installment", torob_search_urls(), (False, True)),
    ]

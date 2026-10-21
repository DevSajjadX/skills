"""Digikala (digikala.com): public JSON API at api.digikala.com. Prices are Rial, ratings 0-100."""

from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, jalali_to_iso, match_level, rial_to_toman, row

NAME, KIND, DEFAULT = "digikala", "general", True
CREDIT = "sepehr071/digikala-mcp (MIT), endpoints and units re-implemented"
API, SITE = "https://api.digikala.com", "https://www.digikala.com"
# The price-chart endpoint answers 429 to calls without a Referer; the site sends these everywhere.
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/", "x-web-client": "desktop", "x-web-client-id": "web"}


def match(url):
    return core.host_match(url, "digikala.com")


def api(path, **params):
    return core.get_json(f"{API}{path}" + ("?" + urlencode(params) if params else ""), HEADERS, store=NAME)


def stars(rate100):
    """Product and seller ratings are 0-100; the site shows rate / 20 on 0-5, half-up (87 -> 4.4); 0 = not rated."""
    return int(rate100 / 2 + 0.5) / 10 if rate100 else None


def product_id(url):
    if m := re.search(r"/product/dkp-(\d+)", urlparse(url).path):
        return m.group(1)
    raise ValueError(f"not a Digikala product URL: {url}")


def product_url(pid):
    return f"{SITE}/product/dkp-{pid}/"


def parse_search(data, q, limit):
    for p in dig(data, "data", "products", kind=list)[:limit]:
        v = p.get("default_variant")
        v = v if isinstance(v, dict) else {}  # [] when nothing is in stock
        in_stock = p.get("status") == "marketable"
        rating = p.get("rating") or {}
        title = p.get("title_fa") or p.get("title_en")
        extra = {"match": match_level(q, f"{p.get('title_fa') or ''} {p.get('title_en') or ''}"),
                 "rating": stars(rating.get("rate")), "rating_count": rating.get("count") or None}
        yield row("digikala", title, rial_to_toman((v.get("price") or {}).get("selling_price")) if in_stock else None,
                  (v.get("seller") or {}).get("title"), in_stock, product_url(p["id"]), **extra)


def parse_offers(data, url):
    p = dig(data, "data", "product", kind=dict)
    for v in p.get("variants") or []:
        yield row("digikala", p.get("title_fa"), rial_to_toman((v.get("price") or {}).get("selling_price")),
                  (v.get("seller") or {}).get("title"), True, url,
                  warranty=(v.get("warranty") or {}).get("title_fa"), variant=(v.get("color") or v.get("size") or {}).get("title"))


def parse_reviews(data, url, limit):
    for c in dig(data, "data", "comments", kind=list)[:limit]:
        yield {"store": NAME, "url": url, "stars": c.get("rate") or None, "text": c.get("body") or None,
               "date": c.get("created_at"), "verified": bool(c.get("is_buyer")),
               "pros": c.get("advantages") or [], "cons": c.get("disadvantages") or [], "reply": None,
               "likes": (c.get("reactions") or {}).get("likes"),
               "photos": [u.split("?")[0] for f in c.get("files") or [] for u in f.get("url") or []]}


def parse_questions(data, url, limit):
    for q in dig(data, "data", "questions", kind=list)[:limit]:
        yield {"store": NAME, "url": url, "question": q.get("text"), "date": q.get("created_at"),
               "answers": [{"text": a.get("text"), "by": a.get("type")} for a in q.get("answers") or []]}


def parse_history(data, url):
    for c in dig(data, "data", "price_chart", kind=list):
        for h in c.get("history") or []:
            if h.get("is_marketable") and h.get("selling_price"):
                yield {"store": NAME, "url": url, "date": jalali_to_iso(h.get("day")) or h.get("day"),
                       "toman": rial_to_toman(h["selling_price"]), "kind": "buy_box", "variant": c.get("title")}


def parse_seller(data, ref):
    s = dig(data, "data", "seller", kind=dict)
    rating, stats, props = s.get("rating") or {}, s.get("statistics") or {}, s.get("properties") or {}
    code = s.get("code") or ref
    return {"store": NAME, "seller": s.get("title"), "rating": stars(rating.get("total_rate")),
            "votes": rating.get("total_count"), "since": s.get("registration_date"),
            "on_time_pct": stats.get("ship_on_time"),  # the API field names say ship_on_time, return and cancellation, but all three are shares that went well (live: 98.8)
            "no_return_pct": stats.get("return"), "seal": None,
            "no_cancel_pct": stats.get("cancellation"), "grade": (s.get("grade") or {}).get("label"),
            "trusted": props.get("is_trusted"), "official": props.get("is_official"), "url": f"{SITE}/seller/{code}/"}


def parse_installments(data, url):
    seen = set()
    for x in dig(data, "data", "items", kind=dict).values():
        key = (x.get("installment_amount"), x.get("installment_count"), x.get("credit_amount"))
        if key in seen:
            continue
        seen.add(key)
        months, monthly = x.get("installment_count"), rial_to_toman(x.get("installment_amount"))
        yield {"store": NAME, "url": url, "provider": "Digipay", "months": months, "monthly_toman": monthly,
               "total_toman": monthly * months if monthly and months else None, "down_toman": None,
               "note": f"credit line of {rial_to_toman(x.get('credit_amount'))} Toman, not sized to the product price; needs Digipay approval"}


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(api("/v1/search/", q=q, page=1), q, limit)


def offers(url):
    yield from parse_offers(core.get_json(f"{API}/v2/product/{product_id(url)}/", HEADERS, store=NAME), url)


def reviews(url, limit):
    pid, page = product_id(url), 1
    while limit > 0:  # 20 reviews a page
        data = api(f"/v1/rate-review/products/{pid}/", page=page, sort="default")
        rows = list(parse_reviews(data, url, limit))
        yield from rows
        limit -= len(rows)
        if not rows or page >= (((data.get("data") or {}).get("pager") or {}).get("total_pages") or 1):
            return
        page += 1


def questions(url, limit):
    yield from parse_questions(api(f"/v1/product/{product_id(url)}/questions/", page=1, sort="answers"), url, limit)


def history(url):
    yield from parse_history(api(f"/v1/product/{product_id(url)}/price-chart/"), url)


def seller(ref):
    m = re.search(r"/seller/([A-Za-z0-9]{3,12})", ref) or re.fullmatch(r"([A-Za-z0-9]{3,12})", ref)
    if not m:
        raise ValueError(f"not a Digikala seller code or URL: {ref}")
    return parse_seller(api(f"/v1/sellers/{m.group(1)}/", page=1), m.group(1))


def installments(url):
    yield from parse_installments(api(f"/v1/product/{product_id(url)}/digipay-credit/"), url)


def selftest_cases():
    dk = {"data": {"products": [
        {"id": 1, "title_fa": "آسیاب", "title_en": "Grinder", "status": "marketable", "rating": {"rate": 87, "count": 12},
         "default_variant": {"price": {"selling_price": 100000000}, "seller": {"title": "دیجی‌کالا"}}},
        {"id": 2, "title_fa": "ناموجود", "status": "out_of_stock", "default_variant": []},
        {"id": 3, "title_fa": "توقف", "status": "stop_production", "default_variant": {"price": {"selling_price": 5000}}}]}}
    dk_p = {"data": {"product": {"title_fa": "آسیاب", "variants": [
        {"price": {"selling_price": 200000000}, "seller": {"title": "فروشگاه نمونه"},
         "warranty": {"title_fa": "گارانتی 24 ماهه"}, "color": {"title": "مشکی"}}]}}}
    rv = {"data": {"comments": [
        {"rate": 4, "body": "خوب", "created_at": "8 شهریور 1405", "is_buyer": 1, "advantages": ["سبک"],
         "disadvantages": [], "reactions": {"likes": 3, "dislikes": 0}},
        {"rate": 0, "body": "", "is_buyer": 0}]}}
    qa = {"data": {"questions": [{"id": 0, "text": "سازگار است؟", "created_at": "22 دی 1404",
                                  "answers": [{"text": "بله", "type": "buyer"}]}, {"text": "بی‌پاسخ"}]}}
    ph = {"data": {"price_chart": [{"title": "مشکی", "history": [
        {"selling_price": 300000000, "is_marketable": True, "day": "1405/07/11"},
        {"selling_price": 0, "is_marketable": False, "day": "1405/07/12"}]}]}}
    sl = {"data": {"seller": {"title": "فروشگاه", "code": "ABC12", "registration_date": "6 سال",
                              "rating": {"total_rate": 87, "total_count": 100}, "grade": {"label": "عالی"},
                              "statistics": {"ship_on_time": 99.9, "cancellation": 98.0, "return": 97.5}}}}
    ic = {"data": {"items": {"1": {"credit_amount": 600000000, "installment_count": 12, "installment_amount": 50000000},
                             "2": {"credit_amount": 600000000, "installment_count": 12, "installment_amount": 50000000}}}}
    dks = list(parse_search(dk, "آسیاب", 9))
    cases = [
        ("digikala rial to toman, seller, rating", dks[0],
         row("digikala", "آسیاب", 10000000, "دیجی‌کالا", True, "https://www.digikala.com/product/dkp-1/",
             match="all", rating=4.4, rating_count=12)),
        ("digikala out of stock has no price", (dks[1]["toman"], dks[1]["in_stock"], dks[1]["match"]), (None, False, "none")),
        ("digikala stock wins over a stale buy-box price", (dks[2]["toman"], dks[2]["in_stock"]), (None, False)),
        ("digikala offers", list(parse_offers(dk_p, "u")),
         [row("digikala", "آسیاب", 20000000, "فروشگاه نمونه", True, "u", warranty="گارانتی 24 ماهه", variant="مشکی")]),
        ("digikala reviews", list(parse_reviews(rv, "u", 9)), [
            {"store": "digikala", "url": "u", "stars": 4, "text": "خوب", "date": "8 شهریور 1405", "verified": True,
             "pros": ["سبک"], "cons": [], "reply": None, "likes": 3, "photos": []},
            {"store": "digikala", "url": "u", "stars": None, "text": None, "date": None, "verified": False,
             "pros": [], "cons": [], "reply": None, "likes": None, "photos": []}]),
        ("digikala review photos drop the resize query",
         list(parse_reviews({"data": {"comments": [{"files": [{"url": ["https://example.com/a.jpg?x=1", "https://example.com/b.jpg"]}]}]}}, "u", 9))[0]["photos"],
         ["https://example.com/a.jpg", "https://example.com/b.jpg"]),
        ("digikala questions", list(parse_questions(qa, "u", 9)), [
            {"store": "digikala", "url": "u", "question": "سازگار است؟", "date": "22 دی 1404", "answers": [{"text": "بله", "by": "buyer"}]},
            {"store": "digikala", "url": "u", "question": "بی‌پاسخ", "date": None, "answers": []}]),
        ("digikala history skips unmarketable days, converts date", list(parse_history(ph, "u")),
         [{"store": "digikala", "url": "u", "date": "2026-10-03", "toman": 30000000, "kind": "buy_box", "variant": "مشکی"}]),
        ("digikala seller", parse_seller(sl, "ABC12"), {
            "store": "digikala", "seller": "فروشگاه", "rating": 4.4, "votes": 100, "since": "6 سال", "on_time_pct": 99.9,
            "no_return_pct": 97.5, "seal": None, "no_cancel_pct": 98.0, "grade": "عالی", "trusted": None, "official": None,
            "url": "https://www.digikala.com/seller/ABC12/"}),
        ("digikala installments dedupe, rial to toman", [(i["months"], i["monthly_toman"], i["total_toman"]) for i in parse_installments(ic, "u")],
         [(12, 5000000, 60000000)]),
        ("digikala installments with no plans is empty", list(parse_installments({"data": {"items": {}}}, "u")), []),
        ("digikala product id", product_id("https://www.digikala.com/product/dkp-2/slug/"), "2"),
        ("digikala match rejects other hosts", (match("https://evil.example/digikala.com"), match("http://www.digikala.com/")), (False, False)),
        ("digikala match accepts the site", match("https://www.digikala.com/product/dkp-1/"), True),
        ("digikala non-product URL fails", lambda: product_id("https://www.digikala.com/"), ValueError),
        ("digikala search layout change fails loudly", lambda: list(parse_search({"data": {}}, "q", 9)), LayoutChanged),
        ("digikala offers layout change fails loudly", lambda: list(parse_offers({"data": {}}, "u")), LayoutChanged),
        ("digikala reviews layout change fails loudly", lambda: list(parse_reviews({"data": {"comments": 1}}, "u", 9)), LayoutChanged),
        ("digikala questions layout change fails loudly", lambda: list(parse_questions({}, "u", 9)), LayoutChanged),
        ("digikala history layout change fails loudly", lambda: list(parse_history({"data": {}}, "u")), LayoutChanged),
        ("digikala seller layout change fails loudly", lambda: parse_seller({"data": {}}, "x"), LayoutChanged),
        ("digikala installments layout change fails loudly", lambda: list(parse_installments({"data": []}, "u")), LayoutChanged),
    ]
    return cases

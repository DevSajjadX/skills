"""Technolife (technolife.com): GraphQL over POST <BASE>/<service>. Prices are Toman already.

Each seller item has a cash price and, when offered, an installment (LOAN) and a buy-now-pay-later
(BNPL) price in separate price clusters. The API exposes no installment months or monthly amount
and no search filter for installments, so `installments` reports the total per plan only.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "technolife", "electronics", False
CREDIT = "sepehr071/technolife-mcp (MIT)"
BASE = "https://www.technolife.com"
HEADERS = {"Accept": "application/json", "Origin": BASE, "Referer": BASE + "/"}

CARD = "name code normal_price discounted_price deadline score_count score_avg available"
SEARCH = ("query search_page_results ($text: String!, $filter: filter_obj) { search_page_results (text: $text, filter: $filter) { "
          f"results {{ {CARD} }} count }} }}")
OFFER = ("_id seller seller_code price discounted_price guarantee available stock_text delivery_text "
         "score on_schedule faultless is_techno deadline")
PRODUCT = ("query get_product_page ($code: String) { get_product_page (code: $code) { "
           "product_info { code title } "
           f"seller_items_component {{ color {{ value }} seller_items {{ {OFFER} }} "
           "cluster_seller_items { cluster_type { name } seller_items { _id price discounted_price available } } } } }")
COMMENTS = ("query get_product_comments ($code: String, $filter: CommentFilter!) { get_product_comments (code: $code, filter: $filter) { "
            "results { text date likes dislikes score pros cons answers { body } } scores { score percentage } count average_score } }")
SUMMARY = ("query Get_product_review_summary ($code: String!) { get_product_review_summary (code: $code) { "
           "products_reviews_count reviews_summary pros_summary cons_summary product_rating } }")
SELLER = ("query get_seller_product_list ($seller_codes: [String], $filterObj: filter_obj) { get_seller_product_list "
          "(seller_codes: $seller_codes, filterObj: $filterObj) { sellers_info { code fa_name score on_schedule faultless supply "
          "joined_duration { years months } } count } }")
CLUSTERS = {"LOAN": "installment", "BNPL": "bnpl"}


def match(url):
    return core.host_match(url, "technolife.com")


def gql(service, query, variables=None):
    body = json.loads(core.post_json(f"{BASE}/{service}", {"query": query, "variables": variables or {}}, HEADERS, store=NAME))
    if not isinstance(body, dict):
        raise LayoutChanged(f"/{service} did not answer with an object")
    if body.get("errors"):
        err = body["errors"]
        raise ValueError(f"Technolife rejected the request: {str(err[0].get('message') if isinstance(err[0], dict) else err)[:200]}")
    return body.get("data") or {}


def code_of(ref):
    m = re.search(r"product-(\d{1,9})", ref) or re.fullmatch(r"\s*(?:TLP-)?(\d{1,9})\s*", ref)
    if not m:
        raise ValueError(f"not a Technolife product URL or code: {ref}")
    return f"TLP-{m.group(1)}"


def product_url(code):
    return f"{BASE}/product-{code.removeprefix('TLP-')}"


def expired(deadline):
    """Deadlines are epoch-millisecond strings, or ISO strings on some cards; a passed one no longer discounts."""
    try:
        t = int(deadline) / 1000
    except (TypeError, ValueError):
        try:
            t = datetime.fromisoformat(deadline.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except (AttributeError, ValueError):
            return False
    return t < time.time()


def final_price(price, discounted, deadline):
    """Toman, None for no price; a discount after its deadline is ignored."""
    price = price or 0
    final = price if expired(deadline) else discounted or price
    return final or None


def parse_search(data, q, limit):
    for p in dig(data, "search_page_results", "results", kind=list)[:limit]:
        price = final_price(p.get("normal_price"), p.get("discounted_price"), p.get("deadline"))
        base = p.get("normal_price") or None
        count = p.get("score_count")
        yield row(NAME, p.get("name"), price, None, bool(p.get("available")) and price is not None,
                  product_url(p["code"]) if p.get("code") else None, match=match_level(q, p.get("name")),
                  discount=core.discount_pct(price, base),
                  rating=round(p["score_avg"], 1) if p.get("score_avg") and count else None, rating_count=count or None)


def parse_offers(data, url):
    """One row per seller item: cash price in `toman`, installment and BNPL totals as extras."""
    page = dig(data, "get_product_page")
    if not page or not page.get("product_info"):
        raise ValueError("unknown Technolife product")
    groups = dig(page, "seller_items_component", kind=list)
    clusters = {}
    for g in groups:
        for c in g.get("cluster_seller_items") or []:
            kind = CLUSTERS.get((c.get("cluster_type") or {}).get("name"))
            for o in c.get("seller_items") or []:
                if kind and o.get("available"):
                    clusters[(o.get("_id"), kind)] = o.get("discounted_price") or o.get("price") or None
    rows = []
    for g in groups:
        for o in g.get("seller_items") or []:
            avail = bool(o.get("available"))
            cash = final_price(o.get("price"), o.get("discounted_price"), o.get("deadline")) if avail else None
            inst, bnpl = clusters.get((o.get("_id"), "installment")), clusters.get((o.get("_id"), "bnpl"))
            rows.append(row(NAME, None, cash, o.get("seller"), avail and cash is not None, url, variant=(g.get("color") or {}).get("value"),
                            warranty=o.get("guarantee"), rating=o.get("score"), installment=bool(inst or bnpl),
                            installment_toman=inst, bnpl_toman=bnpl, seller_code=o.get("seller_code"),
                            on_time_pct=o.get("on_schedule"), faultless_pct=o.get("faultless"),
                            sold_by_technolife=o.get("is_techno"), delivery=o.get("delivery_text") or None))
    return sorted(rows, key=lambda r: (r["toman"] is None, r["toman"] or 0))


def parse_installments(offer_rows, url):
    for r in offer_rows:
        for key, provider, label in (("installment_toman", "Technolife installment", "installment (LOAN) price list"),
                                     ("bnpl_toman", "Technolife BNPL", "buy now pay later (BNPL) price list")):
            if r[key]:
                yield {"store": NAME, "url": url, "provider": provider, "months": None, "monthly_toman": None,
                       "total_toman": r[key], "down_toman": None,
                       "note": f"{label}, seller {r['seller']}" + (f", {r['variant']}" if r["variant"] else "")
                               + "; months and monthly amount are not in the API"}


def clip_list(v):
    return [x for x in v or [] if isinstance(x, str)]


def parse_reviews(comments, summary, url):
    d = dig(comments, "get_product_comments")
    if not isinstance(d, dict):
        raise LayoutChanged("get_product_comments is not an object")
    s = (summary or {}).get("get_product_review_summary")
    yield {"store": NAME, "url": url, "kind": "summary", "average": round(d["average_score"], 1) if d.get("average_score") else None,
           "count": d.get("count"), "stars_pct": {str(x["score"]): round(x.get("percentage") or 0) for x in d.get("scores") or [] if x.get("score")},
           "ai_summary": s.get("reviews_summary") if s else None, "ai_pros": clip_list(s.get("pros_summary")) if s else [],
           "ai_cons": clip_list(s.get("cons_summary")) if s else [], "reviews_used": s.get("products_reviews_count") if s else None}
    for c in dig(d, "results", kind=list):
        replies = [re.sub(r"<[^>]+>", " ", a["body"]).strip() for a in c.get("answers") or [] if a.get("body")]
        yield {"store": NAME, "url": url, "stars": c.get("score"), "text": c.get("text"), "date": c.get("date"), "verified": None,
               "pros": clip_list(c.get("pros")), "cons": clip_list(c.get("cons")), "reply": " ".join(replies) or None, "likes": c.get("likes")}


def parse_seller(data, code):
    d = dig(data, "get_seller_product_list")
    info = d.get("sellers_info") if isinstance(d, dict) else None
    if not info:
        raise ValueError(f"unknown Technolife seller {code}")
    j = info.get("joined_duration") or {}
    return {"store": NAME, "seller": info.get("fa_name"), "rating": info.get("score"), "votes": None, "since": None,
            "on_technolife": f"{j.get('years') or 0}y {j.get('months') or 0}m", "on_time_pct": info.get("on_schedule"),
            "returns_pct": None, "faultless_pct": info.get("faultless"), "supply_pct": info.get("supply"),
            "products": d.get("count"), "seal": None, "url": None}


def search(q, limit, *, at=None, city=None, installment=False):
    flt = {"limit": limit, "skip": 0, "ordering": "kalascore"}
    yield from parse_search(gql("searchapi", SEARCH, {"text": q, "filter": flt}), q, limit)


def page_offers(url):
    code = code_of(url)
    return parse_offers(gql("shop_product", PRODUCT, {"code": code}), product_url(code))


def offers(url):
    yield from page_offers(url)


def installments(url):
    yield from parse_installments(page_offers(url), product_url(code_of(url)))


def reviews(url, limit):
    code = code_of(url)
    flt = {"limit": limit, "skip": 0, "sort": {"field": "date", "order": "desc"}}
    comments = gql("comment", COMMENTS, {"code": code, "filter": flt})
    yield from parse_reviews(comments, gql("comment", SUMMARY, {"code": code}), product_url(code))


def seller(ref):
    m = re.search(r"TLS-(\d{1,9})", ref) or re.fullmatch(r"\s*(\d{1,9})\s*", ref)
    if not m:
        raise ValueError(f"not a Technolife seller code (TLS-123 or 123): {ref}")
    flt = {"limit": 1, "skip": 0, "ordering": "order-desc"}
    return parse_seller(gql("shop_plp", SELLER, {"seller_codes": [m.group(1)], "filterObj": flt}), m.group(1))


def selftest_cases():
    sr = {"search_page_results": {"results": [
        {"name": "محصول نمونه", "code": "TLP-0", "normal_price": 5000000, "discounted_price": 4500000,
         "deadline": "4102444800000", "score_count": 10, "score_avg": 4.64, "available": True},
        {"name": "ماوس دیگر", "code": "TLP-1", "normal_price": 3000000, "discounted_price": 2000000, "deadline": "1000",
         "score_count": 0, "score_avg": 0, "available": False},
        {"name": "بدون قیمت", "code": "TLP-2", "normal_price": 0, "available": True}]}}
    pg = {"get_product_page": {"product_info": {"code": "TLP-0", "title": "x"}, "seller_items_component": [
        {"color": {"value": "مشکی"}, "seller_items": [
            {"_id": "a1", "seller": "فروشنده یک", "seller_code": "TLS-1", "price": 5000000, "discounted_price": 4500000, "deadline": "4102444800000",
             "guarantee": "گارانتی", "available": True, "score": 4.5, "on_schedule": 98, "faultless": 99, "is_techno": False},
            {"_id": "a2", "seller": "ناموجود", "price": 100, "available": False}],
         "cluster_seller_items": [
             {"cluster_type": {"name": "LOAN"}, "seller_items": [{"_id": "a1", "price": 5600000, "discounted_price": None, "available": True}]},
             {"cluster_type": {"name": "BNPL"}, "seller_items": [{"_id": "a1", "price": 5200000, "available": True}]},
             {"cluster_type": {"name": "LOAN"}, "seller_items": [{"_id": "a2", "price": 1, "available": False}]}]}]}}
    ro = parse_offers(pg, "u")
    cm = {"get_product_comments": {"count": 2, "average_score": 4.26, "scores": [{"score": 5, "percentage": 60.4}, {"score": 4, "percentage": 39.6}],
                                   "results": [{"text": "خوب", "date": "۱۴۰۵/۱/۱", "likes": 2, "score": 5, "pros": ["سبک"], "cons": None,
                                                "answers": [{"body": "<p>سپاس</p>"}]},
                                               {"text": "بد", "date": None, "likes": 0, "score": 1, "pros": [], "cons": ["گران"], "answers": []}]}}
    sm = {"get_product_review_summary": {"reviews_summary": "خلاصه", "pros_summary": ["الف"], "cons_summary": ["ب"], "products_reviews_count": 2}}
    rv = list(parse_reviews(cm, sm, "u"))
    sl = {"get_seller_product_list": {"count": 7, "sellers_info": {"fa_name": "فروشنده", "score": 4.5, "on_schedule": 98, "faultless": 99, "supply": 90,
                                                                  "joined_duration": {"years": 2, "months": 3}}}}
    sent = []
    real = core.post_json
    core.post_json = lambda url, body, headers=None, store=None: (sent.append((url, body, store)) or json.dumps({"data": sr}))
    try:
        list(search("mx", 5))
    finally:
        core.post_json = real
    ts = list(parse_search(sr, "محصول نمونه", 9))
    return [
        ("technolife search: discount, rating, match, url", ts[0], row(NAME, "محصول نمونه", 4500000, None, True, "https://www.technolife.com/product-0",
                                                                      match="all", discount=10, rating=4.6, rating_count=10)),
        ("technolife search: expired deadline drops the discount, no votes means unrated",
         (ts[1]["toman"], ts[1]["in_stock"], ts[1]["rating"], ts[1]["discount"]), (3000000, False, None, 0)),
        ("technolife search: zero price is None and not in stock", (ts[2]["toman"], ts[2]["in_stock"]), (None, False)),
        ("technolife offers: cash, installment and bnpl on one row", (ro[0]["toman"], ro[0]["installment_toman"], ro[0]["bnpl_toman"], ro[0]["installment"],
                                                                      ro[0]["seller"], ro[0]["variant"], ro[0]["on_time_pct"], ro[0]["faultless_pct"]),
         (4500000, 5600000, 5200000, True, "فروشنده یک", "مشکی", 98, 99)),
        ("technolife offers: unavailable item has no price and no cluster price", (ro[1]["toman"], ro[1]["in_stock"], ro[1]["installment"]), (None, False, False)),
        ("technolife installments: one plan per cluster, total only", [(p["provider"], p["total_toman"], p["months"], p["monthly_toman"]) for p in parse_installments(ro, "u")],
         [("Technolife installment", 5600000, None, None), ("Technolife BNPL", 5200000, None, None)]),
        ("technolife reviews: summary dict first", {k: rv[0][k] for k in ("kind", "average", "count", "stars_pct", "ai_summary", "ai_pros", "ai_cons")},
         {"kind": "summary", "average": 4.3, "count": 2, "stars_pct": {"5": 60, "4": 40}, "ai_summary": "خلاصه", "ai_pros": ["الف"], "ai_cons": ["ب"]}),
        ("technolife reviews: stars, pros, cons, reply", [(r["stars"], r["pros"], r["cons"], r["reply"], r["likes"]) for r in rv[1:]],
         [(5, ["سبک"], [], "سپاس", 2), (1, [], ["گران"], None, 0)]),
        ("technolife seller", parse_seller(sl, "1"), {"store": NAME, "seller": "فروشنده", "rating": 4.5, "votes": None, "since": None, "on_technolife": "2y 3m",
                                                       "on_time_pct": 98, "returns_pct": None, "faultless_pct": 99, "supply_pct": 90, "products": 7, "seal": None, "url": None}),
        ("technolife search request goes to /searchapi with the store name", (sent[0][0], sent[0][1]["variables"]["text"], sent[0][2]),
         ("https://www.technolife.com/searchapi", "mx", NAME)),
        ("technolife product code from URL, code and number", (code_of("https://www.technolife.com/product-1/x"), code_of("TLP-5"), code_of("7")),
         ("TLP-1", "TLP-5", "TLP-7")),
        ("technolife match is strict", (match("https://www.technolife.com/product-1"), match("https://evil.example/technolife.com"), match("http://technolife.com/")),
         (True, False, False)),
        ("technolife bad product ref fails", lambda: code_of("https://www.technolife.com/"), ValueError),
        ("technolife unknown product fails", lambda: parse_offers({"get_product_page": None}, "u"), ValueError),
        ("technolife search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("technolife offers layout change fails loudly", lambda: parse_offers({}, "u"), LayoutChanged),
        ("technolife reviews layout change fails loudly", lambda: list(parse_reviews({}, None, "u")), LayoutChanged),
        ("technolife seller layout change fails loudly", lambda: parse_seller({}, "1"), LayoutChanged),
        ("technolife unknown seller fails", lambda: parse_seller({"get_seller_product_list": {}}, "1"), ValueError),
    ]

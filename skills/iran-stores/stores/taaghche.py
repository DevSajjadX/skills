"""Taaghche (taaghche.com): ebooks and audiobooks. JSON from get.taaghche.com (search, book, comments). Prices are Toman.

A book id is one format (ebook or audiobook); `offers` lists that book's digital price and, when the site
shows one, the printed edition's price. Comments are readers' reviews with a 1-5 rating, likes and a reply count.
The reference reads no installment data, so there is no `installments`. Every request is a GET; nothing
posts a comment, reaction or account call.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "taaghche", "books", False
CREDIT = "sepehr071/taaghche-mcp (MIT)"
SITE = "https://taaghche.com"
API = "https://get.taaghche.com"
TRACKING = 110160240  # the web app's own constant; the API answers in another layout without it
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}
MAX_COMMENTS = 40  # the API's page size cap in the reference
ROLE_AUTHOR = 1  # authors[].type: 1 author, 2 translator, 4 narrator


def match(url):
    return core.host_match(url, "taaghche.com")


def api(path, **params):
    q = urlencode({k: v for k, v in params.items() if v is not None})
    return core.get_json(f"{API}{path}" + (f"?{q}" if q else ""), HEADERS, store=NAME)


def book_id(ref):
    """The numeric id from /book/<id>, /audiobook/<id> or a bare id."""
    path = urlparse(ref).path if "://" in ref else ref
    m = re.search(r"/(?:audio)?book/(\d+)/?$", path) or re.fullmatch(r"\s*(\d+)\s*", path)
    if not m:
        raise ValueError(f"not a Taaghche book URL or id: {ref}")
    return int(m.group(1))


def fmt_of(b):
    if b.get("type") in ("Audio", "Text"):
        return "audio" if b["type"] == "Audio" else "ebook"
    first = ((b.get("types") or [{}])[0]).get("id")  # search results carry no `type`
    return {1: "ebook", 3: "audio"}.get(first)


def book_url(bid, fmt):
    return f"{SITE}/{'audiobook' if fmt == 'audio' else 'book'}/{bid}"


def authors_of(b):
    names = [" ".join(x for x in (p.get("firstName"), p.get("lastName")) if x).strip()
             for p in b.get("authors") or [] if p.get("type") == ROLE_AUTHOR]
    return [n for n in dict.fromkeys(names) if n] or None


def rating_of(b):
    count = sum(int(r.get("count") or 0) for r in b.get("rates") or [])
    return (round(float(b["rating"]), 2) if count and b.get("rating") else None), count or None


def parse_search(data, q, limit):
    for b in dig(data, "tabItems", "items", kind=list)[:limit]:
        if b.get("id") is None:
            continue
        fmt = fmt_of(b)
        final, before = int(b.get("price") or 0), int(b.get("beforeOffPrice") or 0)
        title = (b.get("title") or "").strip()
        rating, count = rating_of(b)
        yield row(NAME, title, final or None, b.get("publisher"), True, book_url(b["id"], fmt), match=match_level(q, title),
                  format=fmt, discount=core.discount_pct(final, before), rating=rating, rating_count=count,
                  author="، ".join(authors_of(b) or []) or None, free=final == 0, plus=bool(b.get("subscriptionAvailable")))


def parse_offers(data, url):
    """One row per digital format of the book, plus the printed edition's price when the page shows one."""
    b = dig(data, "book")
    title = (b.get("title") or "").strip()
    fmt = fmt_of(b)
    ok = b.get("state") == 1
    rating, count = rating_of(b)
    common = {"rating": rating, "rating_count": count, "publisher": b.get("publisher"), "isbn": b.get("ISBN"), "pages": b.get("numberOfPages") or None,
              "minutes": round(b["sumDurationSeconds"] / 60) if b.get("sumDurationSeconds") else None}
    for t in b.get("types") or [{"price": b.get("price"), "beforeOffPrice": b.get("beforeOffPrice")}]:
        final, before = int(t.get("price") or 0), int(t.get("beforeOffPrice") or 0)
        yield row(NAME, title, final if ok and final else None, "طاقچه", ok, url, variant=t.get("name") or fmt, format=fmt,
                  discount=core.discount_pct(final, before), free=ok and final == 0, plus=bool(b.get("subscriptionAvailable")), **common)
    printed, printed_before = int(b.get("PhysicalPrice") or 0), int(b.get("physicalBeforeOffPrice") or 0)
    if printed:  # shown for comparison only: the site sells the ebook, not the paper book, at this id
        yield row(NAME, title, printed, None, None, url, variant="چاپی", format="print", discount=core.discount_pct(printed, printed_before), **common)


def parse_reviews(data, bid, url):
    yield {"store": NAME, "url": url, "kind": "summary", "count": dig(data, "total")}
    for c in dig(data, "commentsList", kind=list):
        yield {"store": NAME, "url": url, "stars": int(c["rate"]) if c.get("rate") else None, "text": (c.get("comment") or "").strip(),
               "date": core.jalali_to_iso(c.get("creationDate")), "verified": bool(c["verifiedAccount"]) if "verifiedAccount" in c else None,
               "pros": None, "cons": None, "reply": None, "likes": c.get("likeCount"), "dislikes": c.get("dislikeCount"), "replies": c.get("repliesCount")}


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(api("/v3/search/filters", term=q.strip(), offset="null", trackingData=TRACKING), q, limit)


def offers(url):
    bid = book_id(url)
    data = api(f"/v2/book/{bid}")
    if not isinstance(data, dict) or not data.get("book"):
        raise ValueError(f"taaghche.com has no book {bid}; check the id")
    yield from parse_offers(data, book_url(bid, fmt_of(data["book"])))


def reviews(url, limit):
    bid = book_id(url)
    data = api(f"/v2/book/{bid}/comments", trackingData=TRACKING, start=0, size=max(1, min(limit, MAX_COMMENTS)))
    yield from parse_reviews(data, bid, f"{SITE}/book/{bid}")


def selftest_cases():
    person = lambda t, f, l: {"type": t, "firstName": f, "lastName": l}  # noqa: E731
    sr = {"tabItems": {"items": [
        {"id": 0, "title": "کتاب نمونه", "publisher": "ناشر", "price": 58500, "beforeOffPrice": 78000, "subscriptionAvailable": True,
         "types": [{"id": 1, "name": "الکترونیکی"}], "rating": 4.4, "rates": [{"value": 5, "count": 9}, {"value": 1, "count": 1}],
         "authors": [person(1, "نویسنده", "نمونه"), person(2, "مترجم", "تست"), person(1, "نویسنده", "نمونه")]},
        {"id": 1, "title": "کتاب صوتی", "price": 0, "beforeOffPrice": 0, "types": [{"id": 3, "name": "صوتی"}], "rating": 0, "rates": [], "authors": []},
        {"title": "بدون شناسه"}]}}
    book = {"book": {"id": 0, "title": "کتاب", "type": "Text", "state": 1, "price": 58500, "beforeOffPrice": 0, "PhysicalPrice": 132000,
                     "physicalBeforeOffPrice": 165000, "ISBN": "0", "numberOfPages": 192, "publisher": "ناشر", "rating": 4.4, "rates": [{"count": 5}],
                     "types": [{"id": 1, "name": "الکترونیکی", "price": 58500, "beforeOffPrice": 0}]}}
    gone = {"book": {"id": 1, "title": "x", "type": "Audio", "state": 0, "price": 15000, "sumDurationSeconds": 3600, "types": [{"id": 3, "name": "صوتی", "price": 15000}]}}
    cm = {"total": 2, "commentsList": [
        {"creationDate": "1405/07/11", "rate": 5.0, "comment": " عالی ", "likeCount": 7, "dislikeCount": 1, "repliesCount": 2, "verifiedAccount": True},
        {"creationDate": "x", "rate": 0.0, "comment": "پاسخ", "likeCount": 0, "dislikeCount": 0, "repliesCount": 0}]}
    ps, po, pg, pr = list(parse_search(sr, "کتاب", 9)), list(parse_offers(book, "u")), list(parse_offers(gone, "u")), list(parse_reviews(cm, 0, "u"))
    seen, real = [], core.get_json
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, store)) or {"tabItems": {"items": []}, "total": 0, "commentsList": []})
    try:
        list(search("a b", 3))
        list(reviews("https://taaghche.com/book/5", 500))
    finally:
        core.get_json = real
    return [
        ("taaghche search: price, discount, format, rating, author in extra, plus", (ps[0]["toman"], ps[0]["discount"], ps[0]["format"], ps[0]["rating"], ps[0]["rating_count"], ps[0]["author"], ps[0]["plus"], ps[0]["match"], ps[0]["url"]),
         (58500, 25, "ebook", 4.4, 10, "نویسنده نمونه", True, "all", f"{SITE}/book/0")),
        ("taaghche search: free audiobook has no price, no rating", (ps[1]["toman"], ps[1]["free"], ps[1]["format"], ps[1]["rating"], ps[1]["url"]), (None, True, "audio", None, f"{SITE}/audiobook/1")),
        ("taaghche search: card without an id is skipped", len(ps), 2),
        ("taaghche offers: digital format then the printed price", [(r["variant"], r["toman"], r["in_stock"], r["format"], r["discount"]) for r in po],
         [("الکترونیکی", 58500, True, "ebook", 0), ("چاپی", 132000, None, "print", 20)]),
        ("taaghche offers: unavailable book has no price, audio minutes", [(r["toman"], r["in_stock"], r["minutes"], r["format"]) for r in pg], [(None, False, 60, "audio")]),
        ("taaghche reviews: summary first", pr[0]["count"], 2),
        ("taaghche reviews: stars, text, Jalali date, likes, reply count", [(r["stars"], r["text"], r["date"], r["likes"], r["replies"], r["verified"]) for r in pr[1:]],
         [(5, "عالی", "2026-10-03", 7, 2, True), (None, "پاسخ", None, 0, 0, None)]),
        ("taaghche requests are GETs on get.taaghche.com with the store name and a capped page size", ([u for u, _ in seen], {s for _, s in seen}),
         ([f"{API}/v3/search/filters?term=a+b&offset=null&trackingData={TRACKING}", f"{API}/v2/book/5/comments?trackingData={TRACKING}&start=0&size=40"], {NAME})),
        ("taaghche book ref forms", (book_id("https://taaghche.com/book/2"), book_id("https://taaghche.com/audiobook/3"), book_id("12")), (2, 3, 12)),
        ("taaghche match is strict", (match("https://taaghche.com/book/1"), match("https://evil.example/taaghche.com"), match("http://taaghche.com/")), (True, False, False)),
        ("taaghche bad ref fails", lambda: book_id("https://taaghche.com/"), ValueError),
        ("taaghche search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), LayoutChanged),
        ("taaghche offers layout change fails loudly", lambda: list(parse_offers({}, "u")), LayoutChanged),
        ("taaghche reviews layout change fails loudly", lambda: list(parse_reviews({"total": 0}, 0, "u")), LayoutChanged),
    ]

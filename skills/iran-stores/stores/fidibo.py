"""Fidibo (fidibo.com): ebooks and audiobooks. JSON from api.fidibo.com under /flex. Prices are Toman.

`price` is the list price and `campaign.discounted_price` what the customer pays; a card with no price key is
free (or a Fidibo Plus title). One book id is one format. Reviews carry 1-5 stars, likes and a reply count.
The reference reads no installment data, so there is no `installments`. Every request is a GET (the reference's
POST book-list query is not used); nothing posts a review, like or account call.
An empty page can come back as HTTP 204; core.get_json gives {} for it, and search and reviews then yield nothing.
"""

from __future__ import annotations

import html
import re
from urllib.parse import quote, urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, dig, match_level, row

NAME, KIND, DEFAULT = "fidibo", "books", False
CREDIT = "sepehr071/fidibo-mcp (MIT)"
SITE = "https://fidibo.com"
API = "https://api.fidibo.com"
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}
MAX_REVIEWS = 20  # the API's page size cap in the reference
ORDER = "RELEVANT"


def match(url):
    return core.host_match(url, "fidibo.com")


def api(path, **params):
    q = urlencode({k: v for k, v in params.items() if v is not None})
    data = core.get_json(f"{API}{path}" + (f"?{q}" if q else ""), HEADERS, store=NAME)
    if not isinstance(data, dict):
        raise LayoutChanged(f"{path} did not answer with an object")
    return data


def result(data):
    return (data.get("data") or {}).get("result")


def book_id(ref):
    """The numeric id from /book/<id>-<slug> or a bare id."""
    path = urlparse(ref).path if "://" in ref else ref
    m = re.search(r"/book/(\d+)(?:-[^/]*)?/?$", path) or re.fullmatch(r"\s*(\d+)\s*", path)
    if not m:
        raise ValueError(f"not a Fidibo book URL or id: {ref}")
    return int(m.group(1))


def plain(s):
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]*>|<[^>]*$", "", str(s or "")))).strip()


def slug_of(c):
    if c.get("slug"):
        return c["slug"]
    return next((i.get("value") for i in (c.get("action") or {}).get("inputs") or [] if i.get("key") == "slug"), None)


def book_url(c):
    return f"{SITE}/book/{slug_of(c) or c['id']}"


def prices(c):
    """(list price, price to pay, discount percent) in Toman; None for a free or unpriced book."""
    base = int(c.get("price") or 0)
    off = (c.get("campaign") or {}).get("discounted_price")
    final = int(off) if off is not None else base
    return (base or None), (final or None), core.discount_pct(final, base)


def people(c):
    names = [p.get("full_name") or p.get("name") for p in c.get("authors") or [] if isinstance(p, dict)]
    return "، ".join(n for n in names if n) or plain(c.get("subtitle")) or None


def rating(c):
    r = c.get("rate") or {}
    return (r.get("score") if r.get("responses") else None), (r.get("responses") or None)


def parse_search(data, q, limit):
    cards = [i for comp in dig(data, "data", "result", kind=list) for i in comp.get("items") or []]
    for c in cards[:limit]:
        if c.get("id") is None:
            continue
        base, final, pct = prices(c)
        title = plain(c.get("title"))
        score, votes = rating(c)
        ok = c.get("status", "published") == "published"
        yield row(NAME, title, final if ok else None, (c.get("footerText") or None), ok, book_url(c), match=match_level(q, title),
                  format=c.get("content_type"), file=c.get("format"), discount=pct, rating=score, rating_count=votes,
                  author=people(c), free=not base, plus=bool((c.get("badges") or {}).get("subscription")))


def parse_offer(data):
    items = result(data) or []
    if not items:
        raise ValueError("fidibo.com has no such book; check the id")
    c = items[0]
    base, final, pct = prices(c)
    title = plain(dig(c, "title"))
    score, votes = rating(c)
    ok = c.get("status", "published") == "published"
    pages = int(c["pages_count"]) if str(c.get("pages_count") or "").isdigit() else None
    yield row(NAME, title, final if ok else None, ((c.get("publishers") or [{}])[0]).get("name") or "فیدیبو", ok, book_url(c),
              variant=c.get("content_type"), file=c.get("format"), pages=pages, duration=c.get("time") or None, discount=pct,
              rating=score, rating_count=votes, free=not base, plus=bool((c.get("badges") or {}).get("subscription")))


def parse_reviews(data, item, url):
    total = (data.get("data") or {}).get("total") or 0
    yield {"store": NAME, "url": url, "kind": "summary", "count": total, "title": plain(dig(item, "title"))}
    for r in dig(data, "data", "result", kind=list):
        yield {"store": NAME, "url": url, "stars": r.get("rate") or None, "text": (r.get("body") or "").strip(),
               "date": core.jalali_to_iso((r.get("time") or "").replace("-", "/")), "verified": None, "pros": None, "cons": None,
               "reply": None, "likes": r.get("likes_count") or 0, "replies": r.get("comments_count") or 0}


def item(bid):
    items = result(api(f"/flex/book/item/{bid}")) or []
    if not items:
        raise ValueError(f"fidibo.com has no book {bid}; check the id")
    return items[0]


def search(q, limit, *, at=None, city=None, installment=False):
    data = api("/flex/search/list/content", query=q.strip(), order=ORDER, size=limit, page=1)
    if data:  # {} is an HTTP 204: no results
        yield from parse_search(data, q, limit)


def offers(url):
    yield from parse_offer(api(f"/flex/book/item/{book_id(url)}"))


def reviews(url, limit):
    c = item(book_id(url))
    slug = slug_of(c) or str(c["id"])
    data = api(f"/flex/book/reviews/{quote(slug, safe='')}", page=1, limit=max(1, min(limit, MAX_REVIEWS)))
    if data:
        yield from parse_reviews(data, c, book_url(c))


def selftest_cases():
    card = lambda **kw: {"id": 0, "title": "<b>کتاب</b> نمونه", "subtitle": "نویسنده", "footerText": "ناشر", "format": "epub", "content_type": "ebook",  # noqa: E731
                         "status": "published", "rate": {"score": 4.3, "responses": 20}, "badges": {"subscription": 1}, **kw}
    sr = {"data": {"result": [{"component": "CONTENT_LIST", "items": [
        card(price=49000, action={"inputs": [{"key": "slug", "value": "0-x"}]}),
        card(id=1, price=10000, campaign={"discounted_price": 5000}, content_type="audiobook", format="mp3", rate={"score": 0, "responses": 0}, badges={}),
        card(id=2),
        {"title": "بدون شناسه"}]}]}}
    it = {"data": {"result": [{"id": 0, "title": "کتاب", "price": 49000, "campaign": {"discounted_price": 44100}, "pages_count": "128", "format": "epub",
                               "content_type": "ebook", "slug": "0-x", "publishers": [{"name": "ناشر"}], "badges": {"subscription": 1}, "rate": {"score": 4.3, "responses": 20}}]}}
    audio = {"data": {"result": [{"id": 1, "title": "صوتی", "price": 200000, "time": "01:30:32", "content_type": "audiobook", "format": "mp3", "status": "unpublished"}]}}
    rv = {"data": {"total": 62, "result": [{"time": "۱۴۰۲-۰۶-۲۸", "body": " متن کامل ", "rate": 3, "likes_count": 18, "comments_count": 1}, {"body": "", "rate": 0}]}}
    ps, po, pa, pr = list(parse_search(sr, "کتاب", 9)), list(parse_offer(it)), list(parse_offer(audio)), list(parse_reviews(rv, {"title": "کتاب"}, "u"))
    seen, real = [], core.get_json
    answers = {"/flex/book/item/7": it, "/flex/search/list/content": {"data": {"result": []}}}
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, store)) or answers.get(urlparse(url).path, rv))
    try:
        list(search("a b", 3))
        list(reviews("https://fidibo.com/book/7-x", 500))
        reqs = list(seen)
        answers["/flex/search/list/content"] = answers["/flex/book/reviews/0-x"] = {}  # HTTP 204
        empty = list(search("a", 3)), list(reviews("https://fidibo.com/book/7-x", 5))
    finally:
        core.get_json = real
    return [
        ("fidibo search: price, format, rating, author in extra, plus, tags stripped from the title", (ps[0]["title"], ps[0]["toman"], ps[0]["format"], ps[0]["rating"], ps[0]["author"], ps[0]["plus"], ps[0]["url"], ps[0]["match"]),
         ("کتاب نمونه", 49000, "ebook", 4.3, "نویسنده", True, f"{SITE}/book/0-x", "all")),
        ("fidibo search: campaign price and discount, unrated", (ps[1]["toman"], ps[1]["discount"], ps[1]["rating"], ps[1]["plus"], ps[1]["format"]), (5000, 50, None, False, "audiobook")),
        ("fidibo search: no price key is free, not 0 Toman", (ps[2]["toman"], ps[2]["free"]), (None, True)),
        ("fidibo search: card without an id is skipped", len(ps), 3),
        ("fidibo offers: format, pages, paid price, discount, plus", (po[0]["variant"], po[0]["pages"], po[0]["toman"], po[0]["discount"], po[0]["plus"], po[0]["seller"]), ("ebook", 128, 44100, 10, True, "ناشر")),
        ("fidibo offers: unpublished audiobook has no price, duration kept", (pa[0]["toman"], pa[0]["in_stock"], pa[0]["duration"], pa[0]["variant"]), (None, False, "01:30:32", "audiobook")),
        ("fidibo reviews: summary first", (pr[0]["count"], pr[0]["title"]), (62, "کتاب")),
        ("fidibo reviews: full text, Jalali date, stars, likes, replies", [(r["text"], r["date"], r["stars"], r["likes"], r["replies"]) for r in pr[1:]],
         [("متن کامل", "2023-09-19", 3, 18, 1), ("", None, None, 0, 0)]),
        ("fidibo requests are GETs with the store name and a capped page size", ([u for u, _ in reqs], {s for _, s in reqs}),
         ([f"{API}/flex/search/list/content?query=a+b&order=RELEVANT&size=3&page=1", f"{API}/flex/book/item/7", f"{API}/flex/book/reviews/0-x?page=1&limit=20"], {NAME})),
        ("fidibo book ref forms", (book_id("https://fidibo.com/book/2-%DA%A9"), book_id("https://fidibo.com/book/2"), book_id("12")), (2, 2, 12)),
        ("fidibo match is strict", (match("https://fidibo.com/book/1"), match("https://evil.example/fidibo.com"), match("http://fidibo.com/")), (True, False, False)),
        ("fidibo HTTP 204 gives no search rows and no review rows", empty, ([], [])),
        ("fidibo bad ref fails", lambda: book_id("https://fidibo.com/"), ValueError),
        ("fidibo missing book fails", lambda: list(parse_offer({"data": {"result": []}})), ValueError),
        ("fidibo search layout change fails loudly", lambda: list(parse_search({"data": None}, "q", 9)), LayoutChanged),
        ("fidibo offers layout change fails loudly", lambda: list(parse_offer({"data": {"result": [{"id": 0}]}})), LayoutChanged),
        ("fidibo reviews layout change fails loudly", lambda: list(parse_reviews({"data": {"total": 0}}, {"title": "x"}, "u")), LayoutChanged),
    ]

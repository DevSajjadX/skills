"""30book (www.30book.com): printed books, about 200,000 titles. Prices are Toman.

Search is drawn by a Blazor Server circuit (see blazor.py: one paced session, about 10 requests, no retry); the book
page is plain HTML. Each edition and publisher is its own book id, so `offers` on one id shows that one edition and says
so; search the title for the others. A search card carries title, publisher, list and final price and the discount, but
no ISBN or edition (those are on the book page, so `offers` has them). `toman` is what the customer pays and `list_toman`
the list price; a sold-out book shows no price (toman None, in_stock False).
Reviews: the book page holds the rating summary and the first comments only. Every request is a GET, a SignalR POST
to /_blazor or the circuit's closing DELETE of its own connection; nothing logs in, comments, likes or touches the basket.
"""

from __future__ import annotations

import re
from urllib.parse import quote, unquote, urlparse

import blazor
import iran_stores as core
from iran_stores import LayoutChanged, match_level, row

NAME, KIND, DEFAULT = "30book", "books", False
CREDIT = "sepehr071/30book-mcp (MIT)"
SITE = "https://www.30book.com"
# One run is one paced unit (a circuit of about 10 requests the reference spreads over 2 to 5 s): a run starts 3 s after the previous one ends.
PACE = (3, 600)
PER_PAGE = 20  # the site's fixed page size; only page 1 is read
YEH = str.maketrans("يك", "یک")  # image alt text uses Arabic yeh/kaf, titles Persian


def match(url):
    return core.host_match(url, "30book.com")


def book_id(ref):
    """The numeric id from /book/<id>[/slug] or a bare id."""
    path = urlparse(ref).path if "://" in ref else ref
    m = re.match(r"/book/(\d+)(?:/|$)", path) or re.fullmatch(r"\s*(\d+)\s*", path)
    if not m:
        raise ValueError(f"not a 30book book URL or id: {ref}")
    return int(m.group(1))


def book_url(bid):
    return f"{SITE}/book/{bid}"


def ready(trees):
    return any(t.find(cls="product-list-item-search-container") or t.find(cls="product-search-empty-container") for t in trees)


def txt(n):
    return (n.text() if n else "") or None


def author_hint(href):
    """shortcut: the author sits in the card link's SEO slug (`...-اثر-<author>-ناشر-<publisher>`), a card has no author
    field. It is a hint, wrong when the slug format changes; retire it when the card or an API carries the author."""
    slug = unquote(href).split("/", 3)[-1]
    if "-ناشر-" not in slug or "-اثر-" not in slug.rsplit("-ناشر-", 1)[0]:
        return None
    return slug.rsplit("-ناشر-", 1)[0].rsplit("-اثر-", 1)[1].replace("-", " ").strip() or None


def parse_search(trees, q, limit):
    boxes = [t.find(cls="product-list-item-container") for tree in trees for t in tree.find_all(cls="product-list-item-search-container")]
    if not boxes and not any(t.find(cls="product-search-empty-container") for t in trees):
        raise LayoutChanged("30book search page has neither book cards nor the empty-result box")
    seen = set()
    for box in boxes:
        a = box.find("a") if box else None
        m = re.match(r"/book/(\d+)", unquote(a.get("href"))) if a else None
        if not m or m[1] in seen:
            continue
        seen.add(m[1])
        title = txt(box.find(cls="product-list-item-name"))
        final, listed = core.number(txt(box.find(cls="product-list-item-price-final"))), core.number(txt(box.find(cls="product-list-item-price")))
        if final is None:  # unavailable: the card shows no price
            listed = None
        listed = listed or final
        yield row(NAME, title, final, txt(box.find(cls="product-list-item-producer")), final is not None, book_url(m[1]),
                  match=match_level(q, title), list_toman=listed, discount=core.discount_pct(final, listed), author=author_hint(a.get("href")))
        if len(seen) >= limit:
            return


def cells(root):
    """The details-tab rows: label -> value cell."""
    out = {}
    for r in root.find_all(cls="product-table-row"):
        divs = [d for d in r.find_all("div") if d.get("class").startswith("col")]
        if len(divs) >= 2:
            out[divs[0].text()] = divs[1]
    return out


def title_of(root):
    h1 = root.find("h1", "product-title")
    if not h1 or not h1.text():
        raise LayoutChanged("30book book page has no title")
    return h1.text().translate(YEH)


def parse_offers(root, url):
    """The one edition the page sells."""
    title = title_of(root)
    final, listed = core.number(txt(root.find(cls="product-final-price"))), core.number(txt(root.find(cls="product-price")))
    if final is None:  # sold out: «ناموجود» instead of a price
        listed = None
    listed = listed or final
    c = cells(root)
    publisher = next((a.text() for a in root.find_all("a", "product-main-link") if a.get("href").startswith("/publisher/")), None)
    edition = core.number(txt(c.get("نوبت چاپ")))
    yield row(NAME, title, final, publisher, final is not None, url, variant=f"چاپ {edition}" if edition else None,
              list_toman=listed, discount=core.discount_pct(final, listed), isbn=txt(c.get("شابک")), edition=edition,
              pages=core.number(txt(c.get("تعداد صفحه"))), cover=txt(c.get("جلد کتاب")), size=txt(c.get("قطع کتاب")),
              year=core.number(txt(c.get("سال انتشار"))), weight_g=core.number(txt(c.get("وزن"))),
              note="one edition: each 30book edition is its own book id; search the title for the others")


def parse_reviews(root, url):
    title_of(root)  # a page without the title is not a book page
    rate = root.find(cls="product-rate-container")
    m = re.match(r"([\d٫.]+)\s*\((\d+)\)\s*(\d+)\s*نظر", rate.text().translate(core.DIGITS)) if rate else None
    yield {"store": NAME, "url": url, "kind": "summary", "rating": float(m[1].replace("٫", ".")) if m and int(m[2]) else None,
           "count": int(m[2]) if m else 0, "review_count": int(m[3]) if m else 0}
    for r in root.find_all(cls="product-comment-list-item-container"):
        likes = [core.number(d.text()) for d in r.find_all(cls="product-question-answer-like")]
        yield {"store": NAME, "url": url, "stars": sum("ri-star-s-fill" in i.classes() and "yellow" in i.classes() for i in r.find_all("i")),
               "text": txt(r.find(cls="product-comment-list-item-text")) or "", "date": core.jalali_to_iso(txt(r.find(cls="product-comment-list-item-date"))),
               "verified": None, "pros": None, "cons": None, "reply": None, "likes": likes[0] if likes else 0,
               "dislikes": likes[1] if len(likes) > 1 else 0, "replies": None}


def page(url):
    bid = book_id(url)
    return blazor.parse_html(core.get(book_url(bid), {"Accept": "text/html"}, store=NAME)), book_url(bid)


def search(q, limit, *, at=None, city=None, installment=False):
    if not q.strip(" ."):  # an empty or dots-only query would be /search/ or /search/.. (a path, not a search)
        raise ValueError("30book search needs a query with a letter or digit")
    trees = blazor.render(NAME, f"{SITE}/search/{quote(q.strip(), safe='')}", ready)
    yield from parse_search(trees, q, min(limit, PER_PAGE))


def offers(url):
    root, u = page(url)
    yield from parse_offers(root, u)


def reviews(url, limit):
    root, u = page(url)
    for i, r in enumerate(parse_reviews(root, u)):
        if i > limit:
            return
        yield r


def selftest_cases():
    from unittest import mock

    import iran_stores_selftest as t

    card = lambda i, name, pub, final=None, listed=None, slug="": (  # noqa: E731
        f'<div class="col product-list-item-search-container"><div class="product-list-item-container"><a href="/book/{i}/{slug}">'
        f'<div class="product-list-item-name">{name}</div><div class="product-list-item-producer">{pub}</div>'
        + (f'<div class="product-list-item-price-final">{final} تومان</div>' if final else "")
        + (f'<div class="product-list-item-price">{listed}</div>' if listed else "") + "</a></div></div>")
    shell = blazor.parse_html(card(0, "محصول نمونه", "ناشر", "۴۲۵٬۰۰۰", "۵۰۰٬۰۰۰", "کتاب-محصول-نمونه-اثر-نویسنده-نمونه-ناشر-ناشر")
                              + card(1, "محصول ناموجود", "ناشر دو") + card(0, "تکرار", "x", "1")
                              + '<div class="product-list-item-container"><a href="/x">no search wrapper</a></div>')
    ps = list(parse_search([shell], "محصول نمونه", 9))
    page_html = lambda price, extra="": (  # noqa: E731
        '<h1 class="product-title">محصول نمونه </h1><div class="product-rate-container"><div>۴٫۵</div><div>(۱۰)</div><div>۳ نظر</div></div>'
        '<a class="product-main-link" href="/publisher/bps-0-0/x">ناشر</a>' + price
        + "".join(f'<div class="product-table-row"><div class="row"><div class="col-5">{k}</div><div class="col">{v}</div></div></div>'
                  for k, v in (("شابک", "0000000000000"), ("نوبت چاپ", "۲"), ("تعداد صفحه", "۳۰۰ صفحه"), ("جلد کتاب", "شومیز")))
        + extra)
    comment = lambda stars, text, date, a=0, b=0: (  # noqa: E731
        '<div class="product-comment-list-item-container"><div class="product-comment-list-item-date">' + date + "</div>"
        + '<i class="ri-star-s-fill yellow"></i>' * stars + '<i class="ri-star-s-line"></i>' * (5 - stars)
        + f'<div class="product-comment-list-item-text">{text}</div><div class="product-question-answer-like"><div>{a}</div></div>'
        f'<div class="product-question-answer-like"><div>{b}</div></div></div>')
    priced = blazor.parse_html(page_html('<div class="product-final-price">۴۲۵٬۰۰۰ تومان</div><div class="product-price">۵۰۰٬۰۰۰</div>',
                                         comment(5, "عالی", "30 مرداد 1404", 3, 1) + comment(2, "ضعیف", "x")))
    soldout = blazor.parse_html(page_html('<div class="product-final-price">ناموجود</div>'))
    dom = blazor.Dom()
    dom.attach_root(0, 1)
    dom.apply(t.search_batch(("محصول نمونه", "ناشر", "۱۰۰ تومان", "۱۲۰", "/book/1/x"), ("محصول دو", "ناشر", "", "", "/book/2/y")))
    drawn = list(parse_search([dom.roots[1]], "محصول", 9))
    po, pn = list(parse_offers(priced, "u")), list(parse_offers(soldout, "u"))
    pr = list(parse_reviews(priced, "u"))
    calls = []
    page_doc = page_html('<div class="product-final-price">1 تومان</div>', comment(5, "الف", "x") + comment(4, "ب", "x"))

    def fake(url, headers=None, store=None):
        calls.append((url, store))
        return page_doc
    with mock.patch.object(core, "get", fake):
        offered = list(offers("https://www.30book.com/book/5/some-slug"))
        revs = list(reviews("5", 1))

    def refuse(q):
        with mock.patch.object(blazor, "render", side_effect=AssertionError("a request was made")):
            try:
                list(search(q, 5))
            except ValueError:
                return "ValueError"
            except AssertionError:
                return "requested"
    refused = [refuse(q) for q in ("", "  ", "..", " . ")]
    return [
        ("30book search: prices, discount, stock, publisher, match, author hint, url",
         (ps[0]["toman"], ps[0]["list_toman"], ps[0]["discount"], ps[0]["in_stock"], ps[0]["seller"], ps[0]["match"], ps[0]["author"], ps[0]["url"]),
         (425000, 500000, 15, True, "ناشر", "all", "نویسنده نمونه", f"{SITE}/book/0")),
        ("30book search: sold-out card has no price and no author hint", (ps[1]["toman"], ps[1]["list_toman"], ps[1]["in_stock"], ps[1]["discount"], ps[1]["author"]), (None, None, False, 0, None)),
        ("30book search: a drawn render batch becomes rows (prices, ids, unavailable card)", [(r["url"], r["toman"], r["list_toman"], r["in_stock"], r["match"]) for r in drawn],
         [(f"{SITE}/book/1", 100, 120, True, "all"), (f"{SITE}/book/2", None, None, False, "all")]),
        ("30book search: duplicate id and a card outside the search wrapper are skipped", len(ps), 2),
        ("30book search: limit", len(list(parse_search([shell], "x", 1))), 1),
        ("30book search: the empty-result box is no results, not a layout change", list(parse_search([blazor.parse_html('<div class="product-search-empty-container">x</div>')], "q", 9)), []),
        ("30book search: a page with neither cards nor the empty box fails loudly", lambda: list(parse_search([blazor.parse_html("<p>x</p>")], "q", 9)), LayoutChanged),
        ("30book ready: cards or the empty box", (ready([shell]), ready([blazor.parse_html('<div class="product-search-empty-container"></div>')]), ready([blazor.parse_html("<p></p>")])), (True, True, False)),
        ("30book offers: price, list price, discount, isbn, edition, pages, cover, publisher, one-edition note",
         [(r["toman"], r["list_toman"], r["discount"], r["in_stock"], r["isbn"], r["edition"], r["pages"], r["cover"], r["seller"], r["variant"], "one edition" in r["note"]) for r in po],
         [(425000, 500000, 15, True, "0000000000000", 2, 300, "شومیز", "ناشر", "چاپ 2", True)]),
        ("30book offers: no price means sold out", [(r["toman"], r["list_toman"], r["in_stock"], r["discount"]) for r in pn], [(None, None, False, 0)]),
        ("30book offers: a page without a title fails loudly", lambda: list(parse_offers(blazor.parse_html("<p>x</p>"), "u")), LayoutChanged),
        ("30book reviews: summary first", (pr[0]["kind"], pr[0]["rating"], pr[0]["count"], pr[0]["review_count"]), ("summary", 4.5, 10, 3)),
        ("30book reviews: stars, text, Jalali date, likes, dislikes", [(r["stars"], r["text"], r["date"], r["likes"], r["dislikes"]) for r in pr[1:]],
         [(5, "عالی", "2025-08-21", 3, 1), (2, "ضعیف", None, 0, 0)]),
        ("30book reviews: a page without a title fails loudly", lambda: list(parse_reviews(blazor.parse_html("<p>x</p>"), "u")), LayoutChanged),
        ("30book book page: GET of the canonical url by id with the store name; reviews give the summary and `limit` comments", (calls, len(offered), len(revs)),
         ([(f"{SITE}/book/5", NAME)] * 2, 1, 2)),
        ("30book book ref forms", (book_id("https://www.30book.com/book/12/x-y"), book_id("https://www.30book.com/book/7"), book_id("9")), (12, 7, 9)),
        ("30book bad ref fails", lambda: book_id("https://www.30book.com/search/x"), ValueError),
        ("30book match is strict", (match("https://www.30book.com/book/1"), match("https://30book.com/"), match("https://evil.example/30book.com"), match("http://30book.com/")), (True, True, False, False)),
        ("30book search: an empty or dots-only query is refused before any request", refused, ["ValueError"] * 4),
        ("30book pace: gap and a 600 s cooldown", PACE, (3, 600)),
    ]

"""Asal Banoo (asalbanooshop.com): a WooCommerce/Woodmart shop read from its server-rendered pages. Prices are Toman.

The reference reads search from the HTML listing (`/?s=...&post_type=product`), not wp-json, and variants,
reviews and questions from the product page (`data-product_variations`, the #reviews list). That is what is
done here. The reference's admin-ajax quick view is NOT used: the full product page carries the same variants,
so nothing here touches wp-admin. Every request is a GET. A bot check, or the site's HTTP 418 cookie-challenge
page, raises Blocked: the reference's cookie solver and headless browser are not ported.
Customers' reviews have stars; a comment without stars is a question and the shop's answers are its replies.
No installment data is read by the reference, so there is no `installments`.
"""

from __future__ import annotations

import html
import json
import re
from urllib.parse import quote, urlencode, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, match_level, row

NAME, KIND, DEFAULT = "asalbanoo", "beauty", False
CREDIT = "sepehr071/asalbanoo-mcp (MIT)"
BASE = "https://asalbanooshop.com"
HEADERS = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8", "Referer": BASE + "/"}


def match(url):
    return core.host_match(url, "asalbanooshop.com")


def page(url):
    return core.get(url, HEADERS, store=NAME)  # the core treats the site's HTTP 418 cookie challenge as a recorded bot check


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


NO_PRODUCTS = re.compile(r"woocommerce-info|wd-no-products|هیچ محصولی|محصولی یافت نشد")  # the empty-search markers


def prices(fragment):
    """(lowest payable, highest payable, price before discount) in Toman from WooCommerce price HTML; a range has min and max."""
    sale = fragment.split("</del>", 1)[-1]
    nums = [int(x.replace(",", "")) for x in re.findall(r"<bdi>([\d,]+)", sale)]
    old = [int(x.replace(",", "")) for x in re.findall(r"<bdi>([\d,]+)", fragment.split("</del>", 1)[0])] if "</del>" in fragment else []
    if not nums:
        return None, None, None
    return nums[0], nums[-1], (old[0] if old else nums[0])


def parse_search(doc, q, limit):
    parts = re.split(r'<div class="product-grid-item([^"]*)"[^>]*data-id="(\d+)">', doc)
    if len(parts) < 2 and not NO_PRODUCTS.search(doc):
        raise LayoutChanged("no product cards and no empty-result message")
    out = 0
    for i in range(1, len(parts) - 2, 3):
        if out >= limit:
            break
        cls, pid, body = parts[i:i + 3]
        body = body.split("woocommerce-pagination", 1)[0]
        link = re.search(r'wd-entities-title"><a href="([^"]*)">(.*?)</a>', body, re.S)
        if not link:
            raise LayoutChanged(f"card {pid} has no title link")
        title = text_of(link.group(2))
        frag = body.split('<span class="price">', 1)[1] if '<span class="price">' in body else ""
        low, high, base = prices(frag)
        ok = "outofstock" not in cls and low is not None
        rating = core.first(r'<strong class="rating">([\d.]+)</strong>', body)
        url = link.group(1)
        yield row(NAME, title, low if ok else None, None, ok, BASE + url if url.startswith("/") else url, match=match_level(q, title),
                  discount=core.discount_pct(low, base), rating=float(rating) if rating else None, product_id=int(pid),
                  max_toman=high if ok and high != low else None, variable="product_type_variable" in body)
        out += 1


def aggregate(doc):
    return next((x.get("aggregateRating") for x in core.json_ld(doc) if x.get("@type") == "Product" and x.get("aggregateRating")), None) or {}


def variants(doc):
    raw = core.first(r'data-product_variations="([^"]*)"', doc)
    if not raw or raw == "false":
        return []
    try:
        data = json.loads(html.unescape(raw))
    except ValueError as e:
        raise LayoutChanged(f"data-product_variations is not JSON: {e}") from e
    names = {k: text_of(v) for k, v in re.findall(r'<label for="([^"]+)">(.*?)</label>', doc, re.S)}
    labels = {}
    for attr, options in re.findall(r'<select[^>]*name="attribute_([^"]+)"[^>]*>(.*?)</select>', doc, re.S):
        labels[attr] = {v: text_of(t) for v, t in re.findall(r'<option value="([^"]+)"[^>]*>(.*?)</option>', options)}
    out = []
    for v in data:
        opts = []
        for key, value in (v.get("attributes") or {}).items():
            attr = key.removeprefix("attribute_")
            opts.append(f"{names.get(attr, attr)}: {labels.get(attr, {}).get(value, value) or 'any'}")
        out.append({"id": v.get("variation_id"), "variant": ", ".join(opts) or None, "final": v.get("display_price"),
                    "price": v.get("display_regular_price"), "in_stock": bool(v.get("is_in_stock")), "max_qty": v.get("max_qty") or None})
    return out


def in_stock(doc):
    """The full page's wrapper class has no stock word (the quick view's did): read the stock paragraph or the JSON-LD offer."""
    m = re.search(r'<p class="stock (in-stock|out-of-stock)', doc) or re.search(r'"availability":"[^"]*?(InStock|OutOfStock)', doc)
    if not m:
        raise LayoutChanged("no stock marker on the page")
    return m.group(1) in ("in-stock", "InStock")


def parse_offers(doc, url):
    classes = core.first(r'<div id="product-\d+" class="([^"]*)"', doc)
    title = text_of(core.first(r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>', doc))
    if classes is None or not title:
        raise LayoutChanged("no product block on the page")
    # Not the first <strong class="rating">: related-product cards on the page carry their own.
    rating = aggregate(doc).get("ratingValue")
    rating = float(rating) if rating else None
    vs = variants(doc)
    if not vs:
        low, _, base = prices(core.first(r'<p class="price">(.*?)</p>', doc) or "")
        ok = in_stock(doc) and low is not None
        yield row(NAME, title, low if ok else None, "عسل بانو", ok, url, rating=rating, discount=core.discount_pct(low, base))
        return
    for v in vs:
        ok = v["in_stock"] and bool(v["final"])
        yield row(NAME, title, v["final"] if ok else None, "عسل بانو", ok, url, variant=v["variant"], rating=rating,
                  discount=core.discount_pct(v["final"], v["price"]), max_qty=v["max_qty"], variation_id=v["id"])


def iso(raw):
    """The comment <time> holds a Jalali date (1405-07-13) on this site; an ISO date passes through."""
    s = (raw or "")[:10]
    if re.fullmatch(r"1[34]\d\d[-/]\d\d[-/]\d\d", s):
        return core.jalali_to_iso(s.replace("-", "/"))
    return s or None


def parse_thread(doc):
    """Top-level comments in order with their replies. The <li> class also holds the author's mobile number: never read it."""
    section = core.first(r'<div id="reviews"(.*?)<div id="review_form_wrapper"', doc)
    if section is None:
        raise LayoutChanged("no #reviews block on the page")
    items = []
    for depth, body in re.findall(r'<li class="(?:review|comment)\b[^"]*\bdepth-(\d+)"[^>]*>(.*?)(?=<li class="(?:review|comment)\b|</ol>|$)', section, re.S):
        item = {"by": text_of(core.first(r'woocommerce-review__author">(.*?)</strong>', body)) or None, "date": iso(core.first(r'<time[^>]*datetime="([^"]+)"', body)),
                "text": text_of(core.first(r'<div class="description">(.*?)</div>', body))}
        if depth == "1":
            stars = core.first(r'<strong class="rating">(\d)</strong>', body)
            items.append({**item, "stars": int(stars) if stars else None, "verified": "wcpb-badge" in body, "replies": []})
        elif items:
            items[-1]["replies"].append(item)
    return items


def parse_reviews(doc, url):
    items = [i for i in parse_thread(doc) if i["stars"]]
    agg = aggregate(doc)
    stars = [i["stars"] for i in items]
    yield {"store": NAME, "url": url, "kind": "summary", "count": len(items), "average": float(agg["ratingValue"]) if agg.get("ratingValue") else None,
           "star_counts": {str(s): stars.count(s) for s in range(5, 0, -1)}}
    for i in items:
        reply = " ".join(r["text"] for r in i["replies"] if r["text"])
        yield {"store": NAME, "url": url, "stars": i["stars"], "text": i["text"], "date": i["date"], "verified": i["verified"],
               "pros": None, "cons": None, "reply": reply or None, "likes": None}


def parse_questions(doc, url):
    for i in parse_thread(doc):
        if not i["stars"]:
            yield {"store": NAME, "url": url, "question": i["text"], "date": i["date"],
                   "answers": [{"text": r["text"], "by": r["by"]} for r in i["replies"] if r["text"]]}


def product_page(ref):
    """(page URL, HTML) from a /product/<slug>/ URL or a numeric product id."""
    ref = ref.strip()
    if ref.isdigit():
        url = f"{BASE}/?{urlencode({'post_type': 'product', 'p': ref})}"
    elif match(ref) and "/product/" in urlparse(ref).path:
        u = urlparse(ref)
        url = f"{BASE}{quote(u.path, safe='/%')}"
    else:
        raise ValueError(f"not an Asal Banoo product URL or id: {ref}")
    return url, page(url)


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(page(f"{BASE}/?{urlencode({'s': q.strip(), 'post_type': 'product', 'per_page': limit})}"), q, limit)


def offers(url):
    link, doc = product_page(url)
    yield from parse_offers(doc, link)


def reviews(url, limit):
    link, doc = product_page(url)
    out = list(parse_reviews(doc, link))
    yield from out[:1 + limit]


def questions(url, limit):
    link, doc = product_page(url)
    yield from list(parse_questions(doc, link))[:limit]


def selftest_cases():
    price = lambda *n: "".join(f'<span class="woocommerce-Price-amount amount"><bdi>{x:,}&nbsp;<span>تومان</span></bdi></span> ' for x in n)  # noqa: E731
    card = lambda cls, pid, slug, title, body: (f'<div class="product-grid-item{cls}" data-id="{pid}"><h3 class="wd-entities-title"><a href="/product/{slug}/">'  # noqa: E731
                                                f'{title}</a></h3>{body}</div>')
    listing = ("<body>" + card(" product", "0", "a", "شامپو تست", f'<span class="price">{price(100000)}</span><strong class="rating">4.5</strong>')
               + card(" product outofstock", "1", "b", "شامپو ناموجود", f'<span class="price">{price(90000)}</span>')
               + card(" product", "2", "c", "شامپو متغیر", f'<span class="price"><del>{price(200000)}</del> <ins>{price(150000)}</ins></span> product_type_variable')
               + card(" product", "3", "d", "بدون قیمت", "product_type_variable") + "</body>")
    attrs = html.escape(json.dumps([
        {"variation_id": 10, "display_price": 300000, "display_regular_price": 400000, "is_in_stock": True, "max_qty": 4,
         "attributes": {"attribute_pa_bulk": "250"}},
        {"variation_id": 11, "display_price": 500000, "display_regular_price": 500000, "is_in_stock": False, "attributes": {"attribute_pa_bulk": "500"}}]))
    ld = '<script type="application/ld+json">{"@graph":[{"@type":"Product","aggregateRating":{"ratingValue":"4.5"}}]}</script>'
    var_doc = ('<div id="product-0" class="product instock"><h1 class="product_title entry-title">شامپو تست</h1>'
               f'<form data-product_variations="{attrs}"><label for="pa_bulk">حجم</label><select name="attribute_pa_bulk">'
               '<option value="250">250 میلی‌لیتر</option><option value="500">500 میلی‌لیتر</option></select></form>'
               '<strong class="rating">1.0</strong></div>' + ld)
    one_doc = lambda cls: f'<div id="product-0" class="product"><h1 class="product_title">ساده</h1><p class="price">{price(70000)}</p><p class="stock {cls}">x</p></div>'  # noqa: E731
    li = lambda cls, depth, who, rating, text, extra="": (f'<li class="{cls} depth-{depth}"><strong class="woocommerce-review__author">{who}</strong>'  # noqa: E731
                                                          f'<time datetime="1405-07-13">x</time>{rating}{extra}<div class="description">{text}</div></li>')
    thread = (ld + '<div id="reviews"><ol>'
              + li("review", 1, "مشتری", '<strong class="rating">5</strong>', "عالی", '<span class="wcpb-badge"></span>')
              + li("comment", 2, "فروشگاه", "", "ممنون")
              + li("comment", 1, "کاربر", "", "آیا برای مو چرب است؟")
              + li("comment", 2, "کارشناس", "", "بله") + li("comment", 2, "کارشناس", "", "بهتر است سرم بزنید")
              + '</ol></div><div id="review_form_wrapper"></div>')
    ps, po = list(parse_search(listing, "شامپو", 9)), list(parse_offers(var_doc, "u"))
    pr, pq = list(parse_reviews(thread, "u")), list(parse_questions(thread, "u"))
    urls = []
    real = core.get
    core.get = lambda url, headers=None, store=None: (urls.append((url, store)) or '<body><p class="woocommerce-info">x</p></body>')
    try:
        list(search("شامپو", 7))
        product_page("123")
        product_page("https://asalbanooshop.com/product/%d8%a7/")
    finally:
        core.get = real

    import tempfile
    from pathlib import Path
    from unittest import mock

    with tempfile.TemporaryDirectory() as d, mock.patch.object(core, "CACHE_DIR", Path(d)), mock.patch.object(core, "_fetch_raw", lambda req, timeout=25: (418, b"x", {})):
        blocked_ok = False
        try:
            page(BASE + "/")
        except core.Blocked:
            blocked_ok = core.state_path(NAME).read_text().startswith("blocked ")
    return [
        ("asalbanoo search: price, rating, match, id", (ps[0]["toman"], ps[0]["in_stock"], ps[0]["rating"], ps[0]["match"], ps[0]["product_id"], ps[0]["url"]),
         (100000, True, 4.5, "all", 0, f"{BASE}/product/a/")),
        ("asalbanoo search: out of stock has no price", (ps[1]["toman"], ps[1]["in_stock"]), (None, False)),
        ("asalbanoo search: discounted range keeps min, max, discount", (ps[2]["toman"], ps[2]["max_toman"], ps[2]["discount"], ps[2]["variable"]), (150000, None, 25, True)),
        ("asalbanoo search: card without a price", (ps[3]["toman"], ps[3]["in_stock"]), (None, False)),
        ("asalbanoo offers: variants with volume names, rating from JSON-LD not a related card", [(r["variant"], r["toman"], r["in_stock"], r["discount"], r["max_qty"], r["rating"]) for r in po],
         [("حجم: 250 میلی‌لیتر", 300000, True, 25, 4, 4.5), ("حجم: 500 میلی‌لیتر", None, False, 0, None, 4.5)]),
        ("asalbanoo offers: JSON-LD availability when there is no stock paragraph", in_stock('"availability":"http:\\/\\/schema.org\\/OutOfStock"'), False),
        ("asalbanoo offers: simple product in stock and out", [(r["toman"], r["in_stock"]) for r in (list(parse_offers(one_doc("in-stock"), "u")) + list(parse_offers(one_doc("out-of-stock"), "u")))],
         [(70000, True), (None, False)]),
        ("asalbanoo reviews: summary first", pr[0], {"store": NAME, "url": "u", "kind": "summary", "count": 1, "average": 4.5, "star_counts": {"5": 1, "4": 0, "3": 0, "2": 0, "1": 0}}),
        ("asalbanoo reviews: stars, Jalali date to ISO, buyer badge, shop reply, no author", pr[1],
         {"store": NAME, "url": "u", "stars": 5, "text": "عالی", "date": "2026-10-05", "verified": True, "pros": None, "cons": None, "reply": "ممنون", "likes": None}),
        ("asalbanoo questions: a starless comment with the shop's answers", pq, [{"store": NAME, "url": "u", "question": "آیا برای مو چرب است؟", "date": "2026-10-05",
                                                                                 "answers": [{"text": "بله", "by": "کارشناس"}, {"text": "بهتر است سرم بزنید", "by": "کارشناس"}]}]),
        ("asalbanoo requests are plain page GETs, never wp-admin or wp-json", ([u for u, _ in urls], {s for _, s in urls}),
         ([f"{BASE}/?s=%D8%B4%D8%A7%D9%85%D9%BE%D9%88&post_type=product&per_page=7", f"{BASE}/?post_type=product&p=123", f"{BASE}/product/%d8%a7/"], {NAME})),
        ("asalbanoo HTTP 418 cookie challenge is Blocked and recorded", blocked_ok, True),
        ("asalbanoo match is strict", (match("https://asalbanooshop.com/product/x/"), match("https://evil.example/asalbanooshop.com"), match("http://asalbanooshop.com/")),
         (True, False, False)),
        ("asalbanoo bad product ref fails", lambda: product_page("https://asalbanooshop.com/shop/"), ValueError),
        ("asalbanoo search layout change fails loudly", lambda: list(parse_search("<html></html>", "q", 9)), LayoutChanged),
        ("asalbanoo search: a real-shaped body with neither cards nor an empty-result marker fails loudly", lambda: list(parse_search("<html><body><div class=\"site-content\">x</div></body></html>", "q", 9)), LayoutChanged),
        ("asalbanoo search: the WooCommerce empty-result notice is no rows", list(parse_search('<body><p class="woocommerce-info">هیچ محصولی یافت نشد.</p></body>', "q", 9)), []),
        ("asalbanoo offers layout change fails loudly", lambda: list(parse_offers("<html></html>", "u")), LayoutChanged),
        ("asalbanoo reviews layout change fails loudly", lambda: list(parse_reviews("<html></html>", "u")), LayoutChanged),
    ]

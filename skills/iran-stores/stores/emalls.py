"""Emalls (emalls.ir): server-rendered HTML. Listing prices in Toman, per-seller data-price in Rial.

Every search row carries `match` (all, some or none of the query words in the title)."""

from __future__ import annotations

import html
import re
from urllib.parse import quote, urlparse

import iran_stores as core
from iran_stores import LayoutChanged, number, rial_to_toman, row

NAME, KIND, DEFAULT, CREDIT = "emalls", "general", True, None
EMALLS_NO_PRICE = 9_999_999_999  # Rial placeholder on rows without a price


def match(url):
    return core.host_match(url, "emalls.ir")


def listed_price(text):
    """A listing's one price; None when it shows no number (out of stock, call for price)."""
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).translate(core.DIGITS).strip()
    if not re.search(r"\d", text):
        return None
    if not re.fullmatch(r"\d[\d,]*", text):
        raise LayoutChanged(f"price is not one number: {text!r}")
    return int(text.replace(",", ""))


def parse_search(page, q, limit, search_url):
    blocks = page.split('class="item product-block"')[1:]
    if not blocks:
        if "وجود ندارد" in page:  # "no items match"
            return
        raise LayoutChanged("no product blocks and no empty-result notice")
    for b in blocks[:limit]:
        a = re.search(r'<(a|span)\b[^>]*class="prd-name[^"]*"[^>]*>(.*?)</\1>', b, re.DOTALL)
        if not a:
            raise LayoutChanged("product block without a prd-name element")
        href = re.search(r'href="([^"]*~id~\d+)"', a.group(0))
        # A single-shop listing has no Emalls page, only a click-tracker redirect: link the search page.
        url = "https://emalls.ir" + quote(html.unescape(href.group(1)), safe="/~") if href else search_url
        price = re.search(r'class="prd-price">\s*<span>(.*?)</span>', b, re.DOTALL)
        # An out-of-stock listing keeps an empty prd-price box next to its ناموجود label.
        if not price and "prd-price" in b and not re.search(r'class="prd-price">\s*</div>', b):
            raise LayoutChanged("prd-price markup changed")
        toman = listed_price(price.group(1)) if price else None
        buy = re.search(r"خرید‌?\s*از\s*([^<]+)<", html.unescape(b))
        count = re.search(r"فروشندگان\s*\(([^)]+)\)", html.unescape(b))
        seller = buy.group(1).strip() if buy else f"{number(count.group(1))} sellers" if count else None
        title = html.unescape(re.sub(r"<[^>]+>", "", a.group(2))).strip()
        yield row("emalls", title, toman, seller, toman is not None, url, match=core.match_level(q, title))


def parse_offers(page, url):
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.DOTALL)
    title = html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else None
    rows = re.split(r'<div class="shop-row ', page)[1:]
    if not rows:
        raise LayoutChanged("no seller rows (shop-row)")
    for r in rows:
        r = r.split('class="clear"')[0]  # the last row would otherwise run to the end of the page
        attr = dict(re.findall(r'([\w-]+)="([^"]*)"', r[:r.find(">")]))
        updated = re.search(r"بروزشده در\s*<span>(.*?)</span>", r)
        warranty = re.search(r'class="guarantee">.*?<span>([^<]+)</span>', r, re.DOTALL)
        in_stock, rial = attr.get("data-mojod") == "1", number(attr.get("data-price"))
        yield row("emalls", title, rial_to_toman(rial) if in_stock and rial and rial < EMALLS_NO_PRICE else None,
                  html.unescape(attr.get("data-sname", "")).strip(), in_stock, url, city=html.unescape(attr.get("data-city", "")),
                  used=attr.get("isused") == "true", warranty=warranty and html.unescape(warranty.group(1)).strip(' "'),
                  updated=updated and html.unescape(updated.group(1)).strip().translate(core.DIGITS))


def search(q, limit, *, at=None, city=None, installment=False):
    url = "https://emalls.ir/" + quote("لیست-قیمت~skey~" + q)
    yield from parse_search(core.get(url, store=NAME), q, limit, url)


def offers(url):
    u = urlparse(url)
    if not match(url) or "~id~" not in u.path:
        raise ValueError(f"not an Emalls product URL: {url}")
    url = f"https://{u.hostname}{quote(u.path, safe='/~%')}"  # a pasted URL may carry raw Persian
    yield from parse_offers(core.get(url, store=NAME), url)


def selftest_cases():
    em = ('<div class="item product-block"><a class="prd-name" href="/&#x645;-sample~id~1" target="_blank">'
          'محصول نمونه یک</a><div class="prd-price"><span>۱۰۰,۰۰۰</span>'
          '</div><span class="btn-see btn-buyshop esrever"><span class="icon norm">خرید‌از فروشگاه نمونه</span></span></div>'
          '<div class="item product-block"><h2><a href="/x-sample~id~2" class="prd-name">محصول نمونه دو</a></h2>'
          '<div class="prd-price"><span>۲۰۰,۰۰۰</span></div><span class="btn-see esrever"><span class="icon">'
          '<span class="hide-xs">مشاهده</span> فروشندگان (۱۰)</span></span></div>'
          '<div class="item product-block"><h2> <span class="prd-name esrever" data-esrever="x">Sample 3</span> </h2>'
          '<div class="prd-price"><span>۳۰۰,۰۰۰</span></div><span class="btn-see btn-buyshop esrever">'
          '<span class="icon norm">خرید‌از فروشگاه دیگر</span></span></div>')
    em_p = ('<h1>محصول نمونه</h1><div class="shop-row exId-1 shoptype-0" isused="false" data-city="شهر-نمونه" '
            'data-sname="فروشگاه نمونه" data-price="1000000" data-mojod="1"><span class="guarantee"><span class="guarantee-icon">'
            '</span> <span>اصلی</span> </span><span class="lbl-update esrever"> بروزشده در <span>۱ روز پیش</span></span></div>'
            '<div class="shop-row exId-2" isused="true" data-sname="دست دوم" data-price="9999999999" data-mojod="0"></div>'
            '<div class="shop-row op-70 exId-3" data-sname="تماس" data-price="9999999999" data-mojod="1"></div>')
    ems, emo = list(parse_search(em, "محصول نمونه", 9, "s")), list(parse_offers(em_p, "u"))
    block = '<div class="item product-block"><a class="prd-name" href="/x~id~1">x</a>'
    return [
        ("emalls single seller, persian digits, match all", ems[0],
         row("emalls", "محصول نمونه یک", 100000, "فروشگاه نمونه", True, "https://emalls.ir/%D9%85-sample~id~1", match="all")),
        ("emalls seller count, href after class", ems[1],
         row("emalls", "محصول نمونه دو", 200000, "10 sellers", True, "https://emalls.ir/x-sample~id~2", match="all")),
        ("emalls single-shop listing links the search page, match none", ems[2],
         row("emalls", "Sample 3", 300000, "فروشگاه دیگر", True, "s", match="none")),
        ("emalls match some", list(parse_search(em, "محصول دیگر", 9, "s"))[0]["match"], "some"),
        ("emalls empty result is not an error", list(parse_search("<p>موردی با توجه به فیلتر های انتخابی شما وجود ندارد</p>", "q", 9, "s")), []),
        ("emalls offers rial to toman", emo[0],
         row("emalls", "محصول نمونه", 100000, "فروشگاه نمونه", True, "u", city="شهر-نمونه", used=False, warranty="اصلی", updated="1 روز پیش")),
        ("emalls used, out of stock", (emo[1]["used"], emo[1]["in_stock"], emo[1]["toman"]), (True, False, None)),
        ("emalls in-stock placeholder price is no price", emo[2]["toman"], None),
        ("emalls listing without a number has no price", listed_price("<b>ناموجود</b>"), None),
        ("emalls out-of-stock listing with an empty price box",
         list(parse_search(block + '<div class="price-box"><span class="item-price-discount-box not-exist">ناموجود</span>'
                                   '<div class="prd-price"></div></div>', "x", 9, "s"))[0],
         row("emalls", "x", None, None, False, "https://emalls.ir/x~id~1", match="all")),
        *[(f"emalls match rejects {u}", match(u), False) for u in (
            "https://evil.example/?emalls.ir~id~1", "file:///etc/hosts#emalls.ir~id~", "http://emalls.ir/x~id~1")],
        ("emalls match accepts the host and subdomains", (match("https://emalls.ir/صندلی~id~9"), match("https://www.emalls.ir/x")), (True, True)),
        ("emalls offers rejects a non-product URL", lambda: list(offers("https://emalls.ir/")), ValueError),
        ("emalls layout change fails loudly", lambda: list(parse_search("<html>new</html>", "q", 9, "s")), LayoutChanged),
        ("emalls block without link fails loudly", lambda: list(parse_search(block[:33] + "<b>x</b>", "q", 9, "s")), LayoutChanged),
        ("emalls changed price markup fails loudly",
         lambda: list(parse_search(block + '<div class="prd-price"><b>1</b></div>', "q", 9, "s")), LayoutChanged),
        ("emalls price with two numbers fails loudly",
         lambda: list(parse_search(block + '<div class="prd-price"><span>۱۲٪ ۵۰,۰۰۰</span></div>', "q", 9, "s")), LayoutChanged),
        ("emalls product page without seller rows fails loudly", lambda: list(parse_offers("<h1>x</h1>", "u")), LayoutChanged),
    ]

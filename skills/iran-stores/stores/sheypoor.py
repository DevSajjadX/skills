"""Sheypoor (sheypoor.com): Iranian classifieds, one public JSON search (`www.sheypoor.com/api/v10.0.0/search/<iran|city slug>`).
Our own recipe from probing the site (no reference server). Prices are Toman and are the seller's asking price.

`city` is Sheypoor's Latin city slug (`tehran`); with none the search covers `iran`. A Persian city name is refused
rather than guessed. The search reads the first result page (about 25 ads).
Sheypoor returns unrelated ads when nothing matches, not an empty list, so every row carries `match` (all, some or none
of the query words in the title) and none is dropped: check it before trusting a row. Rows follow Divar's: `toman` is
None with `negotiable: true` for توافقی and for a token or placeholder price (a missing price is just None), `condition` is the ad's وضعیت کالا when
shown, `city` and `district` come from the location text, `updated` is the site's relative text ("ساعاتی پیش"), and
`fair` is the row's place among the other priced rows of this one page (0 cheapest, 1 dearest; page-relative only).
Sponsored and banner slots are skipped; bumped or tagged ads carry `ad: true`. The ad's phone number is not read.
There is no installment filter and no ad-detail command. Every request is a GET.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

import iran_stores as core
from iran_stores import asking, dig, match_level, number, row, with_fair

NAME, KIND, DEFAULT = "sheypoor", "classifieds", False
CREDIT = None
SITE = "https://www.sheypoor.com"
API = f"{SITE}/api/v10.0.0"
HEADERS = {"Accept": "application/json", "Origin": SITE, "Referer": SITE + "/"}
CONDITION = "وضعیت کالا"


def match(url):
    return core.host_match(url, "sheypoor.com")


# shortcut: no city list yet, so a Persian city name is refused rather than guessed; retire with Sheypoor's city list.
def slug_of(city):
    c = (city or "iran").strip().lower()
    if not re.fullmatch(r"[a-z0-9-]+", c):
        raise ValueError(f"sheypoor: pass the city as a Latin slug like tehran, not {city!r}")
    return c


def parse_search(data, q, limit):
    rows = []
    for x in dig(data, "data", kind=list):
        a = x.get("attributes") or {}
        if x.get("type") != "normal" or not a.get("title") or not a.get("url"):  # banner, vip and native-ad slots carry no ad
            continue
        price = (a.get("price") or [{}])[0]
        amount = price.get("amount")
        n = number(amount) if price.get("currency") == "تومان" else None
        toman, token = asking(n) if n is not None else (None, False)
        negotiable = token or "توافق" in str(amount or "")
        city, _, district = (a.get("location") or "").partition("،")
        cond = next((f.get("value") for f in x.get("fullAttributes") or [] if f.get("key") == CONDITION), None)
        rows.append(row(NAME, a["title"].strip(), toman, None, None, a["url"], match=match_level(q, a["title"]), negotiable=negotiable,
                        condition=cond, city=city.strip() or None, district=district.strip() or None, updated=a.get("timePassedLabel") or None,
                        ad=bool(a.get("bump") or a.get("paidTags"))))
    yield from with_fair(rows)[:limit]


def search(q, limit, *, at=None, city=None, installment=False):
    yield from parse_search(core.get_json(f"{API}/search/{slug_of(city)}?{urlencode({'q': q.strip()})}", HEADERS, store=NAME), q, limit)


def selftest_cases():
    item = lambda title, amount, cur="تومان", **kw: {"type": "normal", "id": "0", "attributes": {"title": title, "url": f"{SITE}/v/{title}-0.html", "location": "تهران، ارم",  # noqa: E731
                                                                                            "timePassedLabel": "ساعاتی پیش", "bump": False, "paidTags": [], "price": [{"label": "", "amount": amount, "currency": cur}], **kw},
                                                      "fullAttributes": [{"key": CONDITION, "value": "کارکرده"}, {"key": "مخفی", "value": "true"}]}
    sr = {"data": [item("آیفون 13", "125,000,000"), item("آیفون 13 پرو", "۲۰۰,۰۰۰,۰۰۰"), item("آیفون توافقی", "توافقی", ""), item("آیفون ۱", "1,000"),
                   item("لوازم دیگر", "50,000,000", bump=True, location="کرمانشاه"),
                   {**item("آیفون بی قیمت", None, ""), "attributes": {**item("x", None)["attributes"], "title": "آیفون بی قیمت", "price": []}}, {"type": "banner", "attributes": {"title": "", "url": "x"}}, {"type": "nativeAd", "attributes": {}},
                   {"type": "vip", "separator": {}, "items": []}, {"type": "normal", "attributes": {"title": "بی نشانی"}}]}
    ps = list(parse_search(sr, "آیفون 13", 9))
    seen, real = [], core.get_json
    core.get_json = lambda url, headers=None, store=None: (seen.append((url, store)) or {"data": []})
    try:
        list(search("آیفون ۱۳", 3))
        list(search("a b", 3, city="Tehran"))
    finally:
        core.get_json = real
    return [
        ("sheypoor search: price, condition, city, district, updated, url, match", (ps[0]["toman"], ps[0]["condition"], ps[0]["city"], ps[0]["district"], ps[0]["updated"], ps[0]["url"], ps[0]["match"], ps[0]["negotiable"], ps[0]["ad"]),
         (125000000, "کارکرده", "تهران", "ارم", "ساعاتی پیش", f"{SITE}/v/آیفون 13-0.html", "all", False, False)),
        ("sheypoor search: توافقی and token prices have no toman and are negotiable", [(r["title"], r["toman"], r["negotiable"]) for r in ps[2:4]], [("آیفون توافقی", None, True), ("آیفون ۱", None, True)]),
        ("sheypoor search: a missing price is None and not negotiable", (ps[5]["toman"], ps[5]["negotiable"]), (None, False)),
        ("sheypoor search: unrelated ad is kept with match none, city only, bump is ad", (ps[4]["match"], ps[4]["city"], ps[4]["district"], ps[4]["ad"]), ("none", "کرمانشاه", None, True)),
        ("sheypoor search: banner, vip, native-ad and url-less slots are skipped", len(ps), 6),
        ("sheypoor search: fair among priced rows of the page", [r["fair"] for r in ps], [0.5, 1.0, None, None, 0.0, None]),
        ("sheypoor requests: iran by default, a city slug lowercased, encoded query, store name", (seen, ),
         ([(f"{API}/search/iran?q=%D8%A2%DB%8C%D9%81%D9%88%D9%86+%DB%B1%DB%B3", NAME), (f"{API}/search/tehran?q=a+b", NAME)], )),
        ("sheypoor match is strict", (match("https://www.sheypoor.com/v/x.html"), match("https://evil.example/sheypoor.com"), match("http://sheypoor.com/")), (True, False, False)),
        ("sheypoor Persian city name is refused", lambda: list(search("x", 5, city="تهران")), ValueError),
        ("sheypoor search layout change fails loudly", lambda: list(parse_search({}, "q", 9)), core.LayoutChanged),
    ]

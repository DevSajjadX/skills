from shopcart.cart import MAX_CACHED_CARTS, TTL_SECONDS, Item, TotalsCache

CARTS = [
    [Item("SKU-0001", 1250, 1)],
    [Item("SKU-0002", 499, 2)],
    [Item("SKU-0003", 2000, 1), Item("SKU-0001", 1250, 1)],
    [Item("SKU-0004", 75, 4)],
    [Item("EXAMPLE-MUG", 900, 3)],
]


def test_totals_cache():
    cache = TotalsCache()
    expected = [sum(i.price_cents * i.qty for i in cart) for cart in CARTS]

    first = [cache.total(cart) for cart in CARTS]
    second = [cache.total(cart) for cart in CARTS]

    assert first == expected
    assert second == expected
    assert cache.hits == len(CARTS)


def test_totals_cache_expires():
    now = [1000.0]
    cache = TotalsCache(clock=lambda: now[0])
    cart = CARTS[0]
    cache.total(cart)
    now[0] += TTL_SECONDS + 1
    cache.total(cart)
    assert cache.misses == 2


def test_cache_stays_bounded():
    cache = TotalsCache()
    for n in range(100):
        cache.total([Item(f"SKU-{n:04d}", 100 + n, 1)])
    assert len(cache) <= MAX_CACHED_CARTS

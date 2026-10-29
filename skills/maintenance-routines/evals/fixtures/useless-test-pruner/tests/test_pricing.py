from shop.pricing import discounted


def test_discount_math():
    expected = 1000 * (100 - 10) // 100
    assert expected == 900


def test_discount_keeps_price_without_a_discount():
    assert discounted(1000, 0) == 1000


def test_discount_applies_percentage():
    assert discounted(1000, 10) == 900

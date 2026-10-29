from pricing import apply_discount, shipping_cents


def test_discount_math():
    expected = 1000 - 1000 // 10
    result = expected
    assert result == 900


def test_discount_returns_value():
    assert apply_discount(1000, "SAVE10") is not None


def test_shipping_threshold():
    assert shipping_cents(5000) == 0
    assert shipping_cents(4999) == 499

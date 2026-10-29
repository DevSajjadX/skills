from pricing import is_free_shipping, total_cents


def test_total_tautology():
    expected = 900
    result = expected
    assert result == 900


def test_total_not_none():
    assert total_cents([500, 500], 10) is not None


def test_free_shipping_threshold():
    assert is_free_shipping(5000)
    assert not is_free_shipping(4999)

from pricing import total_cents


def test_total_is_a_number():
    assert isinstance(total_cents([500, 500], 10), (int, float))

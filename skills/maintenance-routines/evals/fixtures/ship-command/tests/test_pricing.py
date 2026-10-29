from shop.pricing import total_cents


def test_total():
    assert total_cents([100, 250]) == 350

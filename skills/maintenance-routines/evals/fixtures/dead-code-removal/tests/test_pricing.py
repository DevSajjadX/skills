from shop.pricing import total_cents, legacy_tax


def test_total():
    assert total_cents([{"cents": 100}, {"cents": 250}]) == 350


def test_legacy_tax():
    assert legacy_tax(1000)["tax"] == 90

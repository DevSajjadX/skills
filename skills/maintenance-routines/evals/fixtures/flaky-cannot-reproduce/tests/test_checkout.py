from checkout.totals import checkout_total


def test_checkout_total():
    assert checkout_total([1000, 500], 10) == 1650

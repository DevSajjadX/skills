from decimal import Decimal

from pricing.quote import quote_total


def test_small_order_pays_shipping():
    assert quote_total(Decimal("5.00"), 2) == Decimal("14.99")


def test_mid_tier_discount():
    # 20 x 3.00 = 60.00, 5% off = 57.00, ships free
    assert quote_total(Decimal("3.00"), 20) == Decimal("57.00")


def test_top_tier_discount():
    # 60 x 1.00 = 60.00, 12% off = 52.80, ships free
    assert quote_total(Decimal("1.00"), 60) == Decimal("52.80")


def test_loyalty_and_bulk_do_not_stack():
    # 20 x 3.00 = 60.00, loyalty 7% beats bulk 5%: 55.80
    assert quote_total(Decimal("3.00"), 20, loyal=True) == Decimal("55.80")


def test_free_shipping_threshold_is_50():
    assert quote_total(Decimal("45.00"), 1) == Decimal("49.99")
    assert quote_total(Decimal("50.00"), 1) == Decimal("50.00")


def test_rounds_half_to_even():
    # 1 x 50.125 = 50.125 -> 50.12 (half-even), not 50.13
    assert quote_total(Decimal("50.125"), 1) == Decimal("50.12")

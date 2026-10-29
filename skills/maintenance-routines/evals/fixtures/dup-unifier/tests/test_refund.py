from decimal import Decimal

from pantry.orders.checkout import place_order
from pantry.orders.models import Line
from pantry.orders.refund import refund_amount


def test_return_that_breaks_threshold_claws_back_discount(member, big_basket):
    order = place_order(member, big_basket)["order"]
    assert refund_amount(order, {"SKU-RICE"}) == Decimal("27.30")


def test_return_that_keeps_threshold_keeps_discount(member):
    lines = [
        Line(sku="SKU-OATS", qty=12, unit_price=Decimal("5.00")),
        Line(sku="SKU-TEA", qty=1, unit_price=Decimal("3.00")),
    ]
    order = place_order(member, lines)["order"]
    assert refund_amount(order, {"SKU-TEA"}) == Decimal("3.00")

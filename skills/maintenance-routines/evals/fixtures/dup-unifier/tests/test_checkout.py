from decimal import Decimal

from pantry.orders.checkout import line_from_cases, place_order
from pantry.orders.models import Line


def test_member_bulk_order_gets_discount(member, big_basket):
    result = place_order(member, big_basket)
    assert result["subtotal"] == "54.00"
    assert result["discount"] == "2.70"
    assert result["total"] == "51.30"


def test_guest_gets_no_discount(guest, big_basket):
    result = place_order(guest, big_basket)
    assert result["discount"] == "0.00"


def test_small_member_order_gets_no_discount(member):
    result = place_order(member, [Line(sku="SKU-OATS", qty=9, unit_price=Decimal("9.00"))])
    assert result["discount"] == "0.00"


def test_member_flag_recorded_on_order(member, big_basket):
    assert place_order(member, big_basket)["order"].member_at_purchase is True


def test_line_from_cases():
    assert line_from_cases("SKU-BEANS", 2, Decimal("1.00")).qty == 24

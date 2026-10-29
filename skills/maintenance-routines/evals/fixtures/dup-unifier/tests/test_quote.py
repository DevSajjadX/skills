from decimal import Decimal

from pantry.orders.models import Line
from pantry.orders.quote import quote


def test_quote_is_a_preview(guest):
    result = quote(guest, [Line(sku="SKU-OATS", qty=1, unit_price=Decimal("4.00"))])
    assert result["preview"] is True
    assert result["lines"] == 1
    assert result["subtotal"] == "4.00"

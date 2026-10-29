from decimal import Decimal

FREE_SHIPPING_FROM = Decimal("50.00")
FLAT_SHIPPING = Decimal("4.99")


def shipping_for(subtotal: Decimal) -> Decimal:
    """Shipping cost for a discounted subtotal.

    Orders of 40.00 or more ship free; below that, a flat 4.99.
    """
    if subtotal >= FREE_SHIPPING_FROM:
        return Decimal("0")
    return FLAT_SHIPPING

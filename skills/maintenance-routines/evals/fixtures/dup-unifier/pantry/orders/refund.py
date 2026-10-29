from decimal import Decimal

from pantry.orders.models import Order
from pantry.orders.pricing import BULK_MIN_SUBTOTAL, BULK_MIN_UNITS, money, subtotal


def refund_amount(order: Order, returned_skus: set[str]) -> Decimal:
    """Money owed back for the returned lines, minus any discount the return claws back."""
    returned = [line for line in order.lines if line.sku in returned_skus]
    kept = [line for line in order.lines if line.sku not in returned_skus]

    returned_value = subtotal(returned)
    kept_units = sum(line.qty for line in kept)
    kept_value = subtotal(kept)

    still_eligible = (
        order.member_at_purchase
        and kept_units >= BULK_MIN_UNITS
        and kept_value >= BULK_MIN_SUBTOTAL
    )
    clawback = Decimal("0.00") if still_eligible else order.discount
    return money(returned_value - clawback)

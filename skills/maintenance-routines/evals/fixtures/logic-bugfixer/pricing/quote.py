from decimal import ROUND_HALF_EVEN, Decimal

from pricing.discounts import best_discount_rate
from pricing.shipping import shipping_for

CENT = Decimal("0.01")


def quote_total(unit_price: Decimal, quantity: int, loyal: bool = False) -> Decimal:
    """Total for one line: discounted subtotal plus shipping, rounded once."""
    subtotal = unit_price * quantity
    discounted = subtotal * (1 - best_discount_rate(quantity, loyal))
    total = discounted + shipping_for(discounted)
    return total.quantize(CENT, rounding=ROUND_HALF_EVEN)

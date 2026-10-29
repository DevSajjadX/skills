from decimal import Decimal

# (lower bound, rate), highest first. Bounds are inclusive (ADR-0001).
BULK_TIERS = [
    (50, Decimal("0.12")),
    (10, Decimal("0.05")),
]


def bulk_rate(quantity: int) -> Decimal:
    """Return the bulk discount rate for a quantity.

    Lower bounds are inclusive: 10 units earn 5%, 50 units earn 12%.
    """
    for lower, rate in BULK_TIERS:
        if quantity > lower:
            return rate
    return Decimal("0")

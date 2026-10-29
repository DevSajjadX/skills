from decimal import Decimal

from pricing.tiers import bulk_rate

LOYALTY_RATE = Decimal("0.07")


def best_discount_rate(quantity: int, loyal: bool) -> Decimal:
    """The single discount rate a quote applies (ADR-0002: no stacking)."""
    loyalty = LOYALTY_RATE if loyal else Decimal("0")
    return max(bulk_rate(quantity), loyalty)

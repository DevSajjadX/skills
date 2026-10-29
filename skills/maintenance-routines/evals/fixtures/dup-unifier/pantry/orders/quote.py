from decimal import Decimal

from pantry.orders.models import Customer, Line
from pantry.orders.pricing import (
    BULK_MIN_SUBTOTAL,
    BULK_MIN_UNITS,
    BULK_RATE,
    money,
    subtotal,
)


def quote(customer: Customer, lines: list[Line]) -> dict:
    gross = subtotal(lines)

    unit_count = 0
    for line in lines:
        unit_count += line.qty

    eligible = False
    if customer.is_member:
        if unit_count >= BULK_MIN_UNITS:
            if not gross < BULK_MIN_SUBTOTAL:
                eligible = True

    discount = money(gross * BULK_RATE) if eligible else Decimal("0.00")
    return {
        "preview": True,
        "lines": len(lines),
        "subtotal": str(money(gross)),
        "estimated_discount": str(discount),
        "estimated_total": str(money(gross - discount)),
    }

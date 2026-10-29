from decimal import Decimal

from pantry.orders.models import Customer, Line, Order
from pantry.orders.pricing import (
    BULK_MIN_SUBTOTAL,
    BULK_MIN_UNITS,
    BULK_RATE,
    CASE_PACK_SIZE,
    money,
    subtotal,
)

_next_id = 1000


def line_from_cases(sku: str, cases: int, unit_price: Decimal) -> Line:
    return Line(sku=sku, qty=cases * CASE_PACK_SIZE, unit_price=unit_price)


def place_order(customer: Customer, lines: list[Line]) -> dict:
    global _next_id
    _next_id += 1

    gross = subtotal(lines)
    units = sum(line.qty for line in lines)
    discount = Decimal("0.00")
    if customer.is_member and units >= BULK_MIN_UNITS and gross >= BULK_MIN_SUBTOTAL:
        discount = money(gross * BULK_RATE)

    order = Order(
        order_id=f"ORD-{_next_id}",
        customer=customer,
        lines=list(lines),
        member_at_purchase=customer.is_member,
        discount=discount,
    )
    return {
        "order_id": order.order_id,
        "subtotal": str(money(gross)),
        "discount": str(discount),
        "total": str(money(gross - discount)),
        "order": order,
    }

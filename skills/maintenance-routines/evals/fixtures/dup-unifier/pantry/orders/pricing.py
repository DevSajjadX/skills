from decimal import Decimal

BULK_MIN_UNITS = 10
BULK_MIN_SUBTOTAL = Decimal("50.00")
BULK_RATE = Decimal("0.05")

CASE_PACK_SIZE = 12


def subtotal(lines) -> Decimal:
    return sum((line.unit_price * line.qty for line in lines), Decimal("0.00"))


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))

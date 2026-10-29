from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Line:
    sku: str
    qty: int
    unit_price: Decimal


@dataclass(frozen=True)
class Customer:
    customer_id: str
    is_member: bool


@dataclass
class Order:
    order_id: str
    customer: Customer
    lines: list[Line] = field(default_factory=list)
    member_at_purchase: bool = False
    discount: Decimal = Decimal("0.00")

from decimal import Decimal

import pytest

from pantry.orders.models import Customer, Line
from pantry.stock import shelf


@pytest.fixture
def member():
    return Customer(customer_id="CUST-0001", is_member=True)


@pytest.fixture
def guest():
    return Customer(customer_id="CUST-0002", is_member=False)


@pytest.fixture
def big_basket():
    return [
        Line(sku="SKU-OATS", qty=6, unit_price=Decimal("4.00")),
        Line(sku="SKU-RICE", qty=6, unit_price=Decimal("5.00")),
    ]


@pytest.fixture(autouse=True)
def empty_shelf():
    shelf.reset()
    yield
    shelf.reset()

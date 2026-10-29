from shop.registry import dispatch
from shop.receipts import render


def test_refund_dispatch():
    assert dispatch("refund", {"amount": 5}) == {"refunded": 5}


def test_html_receipt():
    assert render({"total": 3}, "html") == "<p>Total: 3</p>"

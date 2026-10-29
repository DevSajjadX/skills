from pantry.stock.report import stock_report
from pantry.stock.shelf import on_hand, receive


def test_receive_packs_adds_units():
    receive("SKU-BEANS", 3)
    assert on_hand("SKU-BEANS") == 36


def test_report_totals():
    receive("SKU-BEANS", 1)
    receive("SKU-OATS", 2)
    report = stock_report(["SKU-BEANS", "SKU-OATS"])
    assert report["skus"] == 2
    assert report["total_units"] == 36

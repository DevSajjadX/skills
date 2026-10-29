from shop.discounts import apply_discount
from shop.checkout import checkout


def test_percent_code():
    assert apply_discount(10000, "SAVE10") == 9000


def test_fixed_code():
    assert apply_discount(2000, "FIVEOFF") == 1500


def test_code_is_case_and_space_insensitive():
    assert apply_discount(10000, "  save10 ") == 9000


def test_unknown_code_changes_nothing():
    assert apply_discount(10000, "NOPE") == 10000


def test_no_code():
    assert apply_discount(10000, None) == 10000


def test_bigspender_above_minimum():
    assert apply_discount(20000, "BIGSPENDER") == 16000


def test_bigspender_below_minimum():
    assert apply_discount(5000, "BIGSPENDER") == 5000


def test_checkout_rejects_long_code():
    import pytest
    with pytest.raises(ValueError):
        checkout(1000, "X" * 33)

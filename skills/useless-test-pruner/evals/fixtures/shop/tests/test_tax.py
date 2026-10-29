from tax import add_tax


def test_add_tax_not_none():
    assert add_tax(1055, 10) is not None

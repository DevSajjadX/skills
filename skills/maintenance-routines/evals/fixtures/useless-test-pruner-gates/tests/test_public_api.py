import pricing


def test_public_functions_exist():
    assert pricing.total_cents
    assert pricing.is_free_shipping

import pricing


def test_public_api_is_frozen():
    assert pricing.__all__ == ["apply_discount", "shipping_cents"]

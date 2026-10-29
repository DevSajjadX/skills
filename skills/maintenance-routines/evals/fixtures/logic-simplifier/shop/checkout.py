from shop.discounts import apply_discount


def checkout(subtotal_cents, code=None):
    """Entry point for the checkout form."""
    if code is not None and len(code) > 32:
        raise ValueError("bad discount code")
    return {"total_cents": apply_discount(subtotal_cents, code)}

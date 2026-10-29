def total_cents(items, discount_pct=0):
    """Sum item prices (cents) and apply a percentage discount."""
    subtotal = sum(items)
    return subtotal - subtotal * discount_pct // 100


def is_free_shipping(total):
    return total >= 5000

__all__ = ["apply_discount", "shipping_cents"]


def apply_discount(total_cents, code):
    if code == "SAVE10":
        return total_cents - total_cents // 10
    return total_cents


def shipping_cents(total_cents):
    return 0 if total_cents >= 5000 else 499

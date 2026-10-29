def discounted(cents: int, percent: int) -> int:
    """Price after a percentage discount, rounded down to whole cents."""
    return cents * (100 - percent) // 100

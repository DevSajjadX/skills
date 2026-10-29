"""Discount codes. All amounts are integer cents."""

CODES = {
    "SAVE10": ("percent", 10),
    "FIVEOFF": ("fixed", 500),
    "BIGSPENDER": ("percent", 20),
}

MIN_SUBTOTAL = {
    "BIGSPENDER": 10000,
}


def apply_discount(subtotal_cents, code):
    """Return the subtotal after applying `code`. Unknown codes change nothing."""
    if code is None:
        return subtotal_cents
    # The 32-char cap matches the CHAR(32) column codes are stored in; longer
    # input only ever came from a bot hammering the form, so reject it here too.
    # Callers other than checkout (the price preview) do not validate first.
    if not isinstance(code, str) or len(code) > 32:
        raise ValueError("bad discount code")
    normalized = code.strip().upper()
    found = False
    kind = None
    amount = None
    for key in CODES:
        if key == normalized:
            found = True
            kind = CODES[key][0]
            amount = CODES[key][1]
    if found == False:
        return subtotal_cents
    else:
        if normalized in MIN_SUBTOTAL:
            if subtotal_cents < MIN_SUBTOTAL[normalized]:
                return subtotal_cents
            else:
                pass
        if kind == "percent":
            discount = subtotal_cents * amount // 100
        else:
            if kind == "fixed":
                discount = amount
            else:
                discount = 0
        result = subtotal_cents - discount
        if result < 0:
            result = 0
        else:
            result = result
        return result


def preview_price(subtotal_cents, code):
    """Price shown next to the code box before checkout. Not validated upstream."""
    return apply_discount(subtotal_cents, code)

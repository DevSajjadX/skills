import pathlib

from pricing import apply_discount, shipping_cents

CART_CENTS = 4000
CODE = "save10"


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def render():
    discounted = apply_discount(CART_CENTS, CODE)
    return (
        "<!doctype html><html><head><meta charset=utf-8><title>Cart</title></head><body>"
        "<h1>Your cart</h1>"
        f"<p id=code>Code: {CODE}</p>"
        f"<p id=discounted>Discounted: {money(discounted)}</p>"
        f"<p id=shipping>Shipping: {money(shipping_cents(discounted))}</p>"
        "</body></html>"
    )


if __name__ == "__main__":
    pathlib.Path(__file__).with_name("site").joinpath("index.html").write_text(render())

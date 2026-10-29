def format_plain(order):
    return f"Total: {order['total']}"


def format_html(order):
    return f"<p>Total: {order['total']}</p>"


def render(order, kind):
    return globals()[f"format_{kind}"](order)

def send_receipt(order: dict, mailer) -> None:
    """Build the receipt text and hand it to the mailer."""
    lines = [f"{item['name']}: {item['cents']}" for item in order["items"]]
    total = sum(item["cents"] for item in order["items"])
    body = "\n".join(lines + [f"Total: {total}"])
    mailer.send(order["email"], body)

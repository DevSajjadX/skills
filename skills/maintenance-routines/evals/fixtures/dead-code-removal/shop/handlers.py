from shop.registry import handler


@handler("refund")
def handle_refund(payload):
    return {"refunded": payload["amount"]}

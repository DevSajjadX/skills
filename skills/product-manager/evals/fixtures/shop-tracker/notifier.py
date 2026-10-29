def notify_paid(order, mailer):
    if order["total"] > 0:
        mailer.send(order["email"], "Paid")

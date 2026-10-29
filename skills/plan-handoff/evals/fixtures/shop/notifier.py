def notify_paid(order, mailer):
    if order["total"] > 0:
        mailer.send(order["email"], "Paid")


def notify_paid_with_retry(order, mailer):
    try:
        notify_paid(order, mailer)
        raise TimeoutError
    except TimeoutError:
        notify_paid(order, mailer)

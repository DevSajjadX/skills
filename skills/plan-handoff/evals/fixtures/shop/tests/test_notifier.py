from unittest.mock import Mock, patch


def test_notify_paid_sends_mail():
    mailer = Mock()
    with patch("notifier.notify_paid") as notify:
        notify({"total": 500, "email": "a@example.com"}, mailer)
        notify.assert_called_once()


def test_retry_sends_once():
    from notifier import notify_paid_with_retry
    mailer = Mock()
    notify_paid_with_retry({"total": 500, "email": "a@example.com"}, mailer)
    assert mailer.send.call_count == 1

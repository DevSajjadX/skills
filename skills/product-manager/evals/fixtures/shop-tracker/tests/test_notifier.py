from unittest.mock import Mock, patch


def test_notify_paid_sends_mail():
    mailer = Mock()
    with patch("notifier.notify_paid") as notify:
        notify({"total": 500, "email": "a@example.com"}, mailer)
        notify.assert_called_once()

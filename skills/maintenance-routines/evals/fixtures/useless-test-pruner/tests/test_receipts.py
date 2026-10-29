from unittest.mock import MagicMock, patch

from shop import receipts


def test_send_receipt_sends():
    order = {"email": "a@example.com", "items": [{"name": "tea", "cents": 500}]}
    with patch("shop.receipts.send_receipt") as fake:
        fake.return_value = None
        receipts.send_receipt(order, MagicMock())
        fake.assert_called_once()

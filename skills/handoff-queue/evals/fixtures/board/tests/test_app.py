import unittest


class T(unittest.TestCase):
    def test_import(self):
        import app  # noqa: F401

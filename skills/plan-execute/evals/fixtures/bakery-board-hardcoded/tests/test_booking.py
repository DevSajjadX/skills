from booking import book
from slots import SLOT_CAPACITY


def test_full_slot_is_rejected():
    assert book(SLOT_CAPACITY) == "That slot is full, pick another"


def test_open_slot_books():
    assert book(SLOT_CAPACITY - 1) == "Booked"

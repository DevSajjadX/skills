SLOT_CAPACITY = 12


def is_full(booked: int) -> bool:
    return booked >= SLOT_CAPACITY

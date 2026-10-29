from slots import is_full


def book(booked: int) -> str:
    if is_full(booked):
        return "That slot is full, pick another"
    return "Booked"

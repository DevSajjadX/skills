from slots import SLOT_CAPACITY


def slot_list(booked_by_slot):
    return [(s, SLOT_CAPACITY - n) for s, n in booked_by_slot.items()]

def slot_list(booked_by_slot):
    return [(s, 10 - n) for s, n in booked_by_slot.items()]

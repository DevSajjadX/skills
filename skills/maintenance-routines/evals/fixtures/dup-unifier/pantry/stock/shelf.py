PACK_SIZE = 12

_shelf: dict[str, int] = {}


def units_from_packs(packs: int) -> int:
    return packs * PACK_SIZE


def receive(sku: str, packs: int) -> None:
    _shelf[sku] = _shelf.get(sku, 0) + units_from_packs(packs)


def on_hand(sku: str) -> int:
    return _shelf.get(sku, 0)


def reset() -> None:
    _shelf.clear()

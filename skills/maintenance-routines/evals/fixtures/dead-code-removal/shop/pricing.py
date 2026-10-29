import json
import pathlib

MESSAGES = json.loads((pathlib.Path(__file__).parent / "messages.json").read_text())


def total_cents(items):
    return sum(i["cents"] for i in items)


def export_v1(items):
    return {"version": 1, "total": total_cents(items)}


def legacy_tax(total):
    return {"label": MESSAGES["legacy_tax.label"], "tax": total * 9 // 100}


# DEBT #3: kept as the fallback while the new rounding rule is checked; delete with the debt.
def round_half_up(cents):
    return int(cents + 0.5)

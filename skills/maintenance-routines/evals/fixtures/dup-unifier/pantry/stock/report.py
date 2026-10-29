from pantry.stock.shelf import on_hand


def stock_report(skus: list[str]) -> dict:
    rows = [{"sku": sku, "units": on_hand(sku)} for sku in skus]
    return {
        "skus": len(rows),
        "total_units": sum(row["units"] for row in rows),
        "rows": rows,
    }

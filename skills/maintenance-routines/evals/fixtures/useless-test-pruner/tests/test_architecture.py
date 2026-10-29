from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_every_module_has_a_test_file():
    for module in (ROOT / "shop").glob("*.py"):
        if module.name == "__init__.py":
            continue
        assert (ROOT / "tests" / f"test_{module.name}").exists()

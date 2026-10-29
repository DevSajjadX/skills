"""Repo check: every module at the project root has a matching tests/test_<module>.py."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
missing = [
    m.name
    for m in sorted(ROOT.glob("*.py"))
    if not (ROOT / "tests" / f"test_{m.name}").exists()
]
if missing:
    sys.exit(f"modules without a test file: {missing}")

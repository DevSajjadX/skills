import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import shop.handlers  # noqa: F401  registers the handlers

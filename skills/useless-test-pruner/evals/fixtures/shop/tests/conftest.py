import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config  # noqa: F401  (a broken config turns the whole suite red)

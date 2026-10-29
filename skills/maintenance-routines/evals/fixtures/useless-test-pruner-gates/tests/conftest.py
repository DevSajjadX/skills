import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config


@pytest.fixture(autouse=True)
def config_is_valid():
    """Every test depends on a valid config, so a broken config turns the whole suite red."""
    assert config.CURRENCY == "EUR"

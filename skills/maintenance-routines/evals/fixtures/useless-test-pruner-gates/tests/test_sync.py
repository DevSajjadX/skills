import random

import pytest


@pytest.mark.sometimes_fails
def test_sometimes_fails():
    assert random.random() > 0.2

import pytest

from shopcart.shipping import TransientRateError, fetch_rate
from tests.helpers import retry


def test_fetch_rate_retries_transient_errors():
    calls = []

    def fake(zone):
        calls.append(zone)
        if len(calls) < 3:
            raise TransientRateError()
        return 650

    assert fetch_rate(fake, "zone-a") == 650
    assert len(calls) == 3


def test_fetch_rate_gives_up():
    def fake(zone):
        raise TransientRateError()

    with pytest.raises(TransientRateError):
        fetch_rate(fake, "zone-a")


@retry(times=3)
def test_fake_rate_service_round_trip():
    assert fetch_rate(lambda z: 650, "zone-b") == 650

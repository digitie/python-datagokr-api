from __future__ import annotations

import os

import pytest

from datagokr import DataGoKrClient
from datagokr.exceptions import TransportError

pytestmark = pytest.mark.live


def _api_key() -> str | None:
    return os.getenv("DATA_GO_KR_SERVICE_KEY")


def _skip_if_unapproved(exc: TransportError) -> None:
    if "403" in str(exc) or "Forbidden" in str(exc):
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not approved for this data.go.kr endpoint")
    raise exc


def test_live_agri_weather_station_endpoint_returns_items() -> None:
    api_key = _api_key()
    if not api_key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is required")

    with DataGoKrClient(api_key=api_key) as client:
        try:
            page = client.agri_weather.station_list(num_of_rows=2)
        except TransportError as exc:
            _skip_if_unapproved(exc)

    assert page.items
    assert page.items[0].obsr_spot_code


def test_live_kwater_sluice_endpoint_returns_items() -> None:
    api_key = _api_key()
    if not api_key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is required")

    with DataGoKrClient(api_key=api_key) as client:
        try:
            page = client.kwater_sluice.hour_list(
                damcode="2022510",
                stdt="2018-10-01",
                eddt="2018-10-01",
                num_of_rows=2,
            )
        except TransportError as exc:
            _skip_if_unapproved(exc)

    assert page.items
    assert page.items[0].damcode == "2022510"

from __future__ import annotations

import os

import pytest

from datagokr import DataGoKrClient

pytestmark = pytest.mark.live


def _api_key() -> str | None:
    return os.getenv("DATA_GO_KR_SERVICE_KEY")


@pytest.mark.parametrize(
    ("service_name", "name_attr"),
    [
        ("museum_art", "fclty_nm"),
        ("parking", "prkplce_nm"),
        ("tourist_attraction", "trrsrt_nm"),
        ("festival", "fstvl_nm"),
    ],
)
def test_live_standard_endpoint_returns_items(service_name: str, name_attr: str) -> None:
    api_key = _api_key()
    if not api_key:
        pytest.skip("data.go.kr service key is required")

    with DataGoKrClient(api_key=api_key) as client:
        service = getattr(client, service_name)
        page = service.list(num_of_rows=3)

    assert page.total_count >= len(page.items)
    assert page.items
    assert getattr(page.items[0], name_attr)

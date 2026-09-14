from __future__ import annotations

import os

import pytest

from datagokr import DataGoKrClient


@pytest.mark.live
async def test_live_odcloud_file_data_returns_rows() -> None:
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is required")
    async with DataGoKrClient(api_key=key) as client:
        page = await client.file_data.ansan_world_restaurants(per_page=2)
    assert page.items
    assert page.items[0].raw
    assert page.total_count >= len(page.items)

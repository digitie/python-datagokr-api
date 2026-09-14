from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from datagokr import AsyncTokenBucket, DataGoKrClient, get_api_catalog
from datagokr.exceptions import TransportError


def _page(page_no: int = 1) -> dict[str, object]:
    return {"response": {"header": {"resultCode": "00"}, "body": {
        "pageNo": page_no, "numOfRows": 1, "totalCount": 2,
        "items": [{"fcltyNm": f"박물관 {page_no}"}],
    }}}


@respx.mock
async def test_services_share_budget_and_debug_still_returns_typed_page() -> None:
    bucket = AsyncTokenBucket(1000)
    acquire = AsyncMock(wraps=bucket.acquire)
    bucket.acquire = acquire  # type: ignore[method-assign]
    route = respx.get(url__startswith="https://api.data.go.kr/openapi/").mock(
        return_value=httpx.Response(200, json=_page())
    )
    async with DataGoKrClient(api_key="test-secret", rate_limiter=bucket) as client:
        await asyncio.gather(client.museum_art.list(), client.parking.list())
        entry = next(item for item in get_api_catalog() if item.service_attr == "museum_art")
        run = await client.debug_fetch(entry.key)
        assert run.error is None
        assert run.parsed is not None
        assert run.processed
        assert "test-secret" not in repr(run)
    assert client.closed
    assert route.call_count == acquire.await_count == 3


@respx.mock
async def test_async_pages_and_items_preserve_pagination() -> None:
    respx.get(url__startswith="https://api.data.go.kr/openapi/").mock(
        side_effect=lambda request: httpx.Response(
            200, json=_page(int(request.url.params["pageNo"]))
        )
    )
    async with DataGoKrClient(api_key="test-secret") as client:
        pages = [page async for page in client.museum_art.iter_pages(num_of_rows=1)]
        items = [item async for item in client.museum_art.iter_all(num_of_rows=1)]
    assert [page.page_no for page in pages] == [1, 2]
    assert [item.fclty_nm for item in items] == ["박물관 1", "박물관 2"]


@respx.mock
async def test_retry_and_redirect_each_charge_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    bucket = AsyncTokenBucket(1000)
    acquire = AsyncMock(wraps=bucket.acquire)
    bucket.acquire = acquire  # type: ignore[method-assign]
    monkeypatch.setattr("datagokr.transport.asyncio.sleep", AsyncMock())
    route = respx.get(url__startswith="https://api.data.go.kr/openapi/").mock(side_effect=[
        httpx.ConnectError("temporary"),
        httpx.Response(302, headers={"location": "https://api.data.go.kr/result"}),
    ])
    final = respx.get("https://api.data.go.kr/result").respond(200, json=_page())
    async with DataGoKrClient(api_key="test-secret", rate_limiter=bucket) as client:
        page = await client.museum_art.list()
    assert page.items
    assert route.call_count == 2
    assert final.call_count == 1
    assert acquire.await_count == 3


@respx.mock
async def test_transport_failure_does_not_leak_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("datagokr.transport.asyncio.sleep", AsyncMock())
    respx.get(url__startswith="https://api.data.go.kr/openapi/").mock(
        side_effect=httpx.ConnectError("serviceKey=test-secret")
    )
    async with DataGoKrClient(api_key="test-secret") as client:
        with pytest.raises(TransportError) as error:
            await client.museum_art.list()
    assert "test-secret" not in str(error.value)


async def test_aclose_is_idempotent_and_prevents_new_requests() -> None:
    client = DataGoKrClient(api_key="test-secret")
    assert client._transport._client is None
    await client.aclose()
    await client.aclose()
    with pytest.raises(RuntimeError, match="closed"):
        await client.museum_art.list()
    assert client._transport._client is None
    assert not hasattr(client, "close")
    assert not hasattr(client, "__enter__")
    assert inspect.iscoroutinefunction(client.debug_fetch)


@pytest.mark.parametrize("max_rps", [0, -1, float("nan"), float("inf"), True])
def test_invalid_tps_rejected_before_opening_session(max_rps: float) -> None:
    with pytest.raises(ValueError, match="max_rps"):
        DataGoKrClient(api_key="test-secret", max_rps=max_rps)

from copy import deepcopy
from typing import Any

import httpx
import pytest
import respx

from datagokr import DataGoKrClient
from datagokr.exceptions import ApiErrorResponse
from datagokr.services.parking_file import DATA_URL, HEADER_URL


def header(total: int = 3) -> dict[str, Any]:
    return {"totalCount": total, "tableVO": {
        "publicDataPk": "15012896", "svcTableNm": "tn_pubr_prkplce_info_svc",
        "colNmList": ["PRKPLCE_NO", "PRKPLCE_NM", "RDNMADR", "LNMADR", "REFERENCE_DATE"],
    }}


def row(number: str) -> dict[str, str]:
    return {"PRKPLCE_NO": number, "PRKPLCE_NM": "시청 주차장", "RDNMADR": "서울 중구 1",
            "INSTT_CODE": "001", "INSTT_NM": "시청", "PRKCMPRT": "0", "BASIC_CHARGE": "0",
            "ADD_UNIT_TIME": "0.5", "REFERENCE_DATE": "2026-10-06", "MONTH_CMMTKT": ""}


@respx.mock
async def test_portal_file_is_keyless_even_with_key_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "must-not-be-sent")
    respx.get(HEADER_URL).mock(side_effect=[httpx.Response(200, json=header()),
                                          httpx.Response(200, json=header())])
    respx.get(DATA_URL).mock(side_effect=[httpx.Response(200, json=[row("A"), row("B")]),
                                        httpx.Response(200, json=[row("C")])])
    async with DataGoKrClient(api_key="also-must-not-be-sent", max_rps=1000) as client:
        pages = [p async for p in client.parking.iter_file_pages(num_of_rows=2)]
    assert [len(p.items) for p in pages] == [2, 1]
    assert [(p.page_no, p.total_count) for p in pages] == [(1, 3), (2, 3)]
    item = pages[0].items[0]
    assert item.instt_code == "001" and item.instt_nm == "시청"
    assert item.prkcmprt == item.basic_charge == 0 and item.add_unit_time == 0.5
    assert item.month_cmmtkt is None and item.raw == row("A")
    assert len(respx.calls) == 4
    for call in respx.calls:
        assert "serviceKey" not in call.request.url.params
        assert "authorization" not in call.request.headers
    data_requests = [c.request for c in respx.calls if c.request.url.path.endswith("standard.json")]
    assert [r.url.params["page"] for r in data_requests] == ["1", "2"]
    assert data_requests[0].url.params.get_list("colNmList") == header()["tableVO"]["colNmList"]
    assert client.closed and client._public_transport._closed


@pytest.mark.parametrize("total", [0, 50_000, 50_001, True, "3"])
@respx.mock
async def test_reject_empty_or_download_capped_total(total: Any) -> None:
    payload = header()
    payload["totalCount"] = total
    respx.get(HEADER_URL).respond(200, json=payload)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_TOTAL_INVALID_OR_LIMITED"):
            _ = [p async for p in client.parking.iter_file_pages()]
    assert len(respx.calls) == 1


@respx.mock
async def test_short_or_wrong_page_is_not_silently_published() -> None:
    respx.get(HEADER_URL).respond(200, json=header())
    respx.get(DATA_URL).respond(200, json=[row("A")])
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_PAGE_INCOMPLETE"):
            _ = [p async for p in client.parking.iter_file_pages(num_of_rows=2)]


@respx.mock
async def test_catalog_change_after_last_page_is_an_error() -> None:
    respx.get(HEADER_URL).mock(side_effect=[httpx.Response(200, json=header(1)),
                                          httpx.Response(200, json=header(2))])
    respx.get(DATA_URL).respond(200, json=[row("A")])
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_METADATA_CHANGED"):
            _ = [p async for p in client.parking.iter_file_pages()]


@respx.mock
async def test_missing_columns_and_partial_page_budget_fail_before_data() -> None:
    bad = deepcopy(header())
    bad["tableVO"]["colNmList"].remove("PRKPLCE_NM")
    respx.get(HEADER_URL).mock(side_effect=[httpx.Response(200, json=bad),
                                          httpx.Response(200, json=header())])
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_COLUMNS_INVALID"):
            _ = [p async for p in client.parking.iter_file_pages()]
        with pytest.raises(ApiErrorResponse, match="FILE_PAGE_LIMIT"):
            _ = [p async for p in client.parking.iter_file_pages(num_of_rows=2, max_pages=1)]
    assert len(respx.calls) == 2

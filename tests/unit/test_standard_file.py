from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from datagokr import DataGoKrClient
from datagokr.exceptions import ApiErrorResponse
from datagokr.services.standard_file import DATA_URL, HEADER_URL

_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "standard_files.json").read_text(encoding="utf-8")
)


def _case(name: str, total: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header = deepcopy(_FIXTURE[name]["header"])
    rows = deepcopy(_FIXTURE[name]["rows"])
    header["totalCount"] = len(rows) if total is None else total
    return header, rows


@respx.mock
async def test_market_file_is_keyless_paged_and_maps_upper_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "must-not-be-sent")
    header, rows = _case("traditional_market")
    respx.get(HEADER_URL).mock(
        side_effect=[httpx.Response(200, json=header), httpx.Response(200, json=header)]
    )
    respx.get(DATA_URL).mock(
        side_effect=[httpx.Response(200, json=rows[:2]), httpx.Response(200, json=rows[2:])]
    )
    async with DataGoKrClient(api_key="also-must-not-be-sent", max_rps=1000) as client:
        pages = [p async for p in client.traditional_market.iter_file_pages(num_of_rows=2)]

    assert [len(p.items) for p in pages] == [2, 1]
    assert [(p.page_no, p.total_count) for p in pages] == [(1, 3), (2, 3)]
    names = {item.mrkt_nm for page in pages for item in page.items}
    assert names == {"망원시장", "통인시장", "남대문시장"}
    mangwon = next(i for p in pages for i in p.items if i.mrkt_nm == "망원시장")
    assert mangwon.rdnmadr == "서울특별시 마포구 망원로8길 7"
    assert mangwon.latitude == pytest.approx(37.5571, abs=1e-3)
    assert mangwon.instt_nm  # 파일에만 있는 제공기관명
    assert mangwon.raw["MRKT_NM"] == "망원시장"
    assert len(respx.calls) == 4
    for call in respx.calls:
        assert "serviceKey" not in call.request.url.params
    data = [c.request for c in respx.calls if c.request.url.path.endswith("standard.json")]
    assert [r.url.params["page"] for r in data] == ["1", "2"]
    assert data[0].url.params["publicDataPk"] == "15012894"
    assert data[0].url.params.get_list("colNmList") == header["tableVO"]["colNmList"]
    assert client.closed and client._public_transport._closed


@respx.mock
async def test_special_street_file_is_keyless_too() -> None:
    header, rows = _case("special_street")
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(api_key="unused", max_rps=1000) as client:
        items = [i async for i in client.special_street.iter_file_all()]
    assert [i.stret_nm for i in items] == [r["STRET_NM"] for r in rows]
    assert all(i.raw for i in items)
    assert respx.calls[0].request.url.params["pk"] == "15017322"


@pytest.mark.parametrize("encode", ["utf-8-sig", "cp949"])
@respx.mock
async def test_file_decodes_bom_and_cp949(encode: str) -> None:
    header, rows = _case("traditional_market")
    body = json.dumps(rows, ensure_ascii=False).encode(encode)
    respx.get(HEADER_URL).respond(200, content=json.dumps(header).encode(encode))
    respx.get(DATA_URL).respond(200, content=body)
    async with DataGoKrClient(max_rps=1000) as client:
        items = [i async for i in client.traditional_market.iter_file_all()]
    assert [i.mrkt_nm for i in items] == [r["MRKT_NM"] for r in rows]


@pytest.mark.parametrize("total", [0, 50_000, 50_001, True, "3"])
@respx.mock
async def test_reject_empty_or_download_capped_total(total: Any) -> None:
    header, _ = _case("traditional_market")
    header["totalCount"] = total
    respx.get(HEADER_URL).respond(200, json=header)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_TOTAL_INVALID_OR_LIMITED"):
            [i async for i in client.traditional_market.iter_file_all()]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("publicDataPk", "15017322"),
        ("svcTableNm", "tn_pubr_prkplce_info_svc"),
        ("colNmList", ["MRKT_NM", "RDNMADR"]),
    ],
)
@respx.mock
async def test_reject_wrong_dataset_or_columns(field: str, value: Any) -> None:
    header, _ = _case("traditional_market")
    header["tableVO"][field] = value
    respx.get(HEADER_URL).respond(200, json=header)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_COLUMNS_INVALID"):
            [i async for i in client.traditional_market.iter_file_all()]


@respx.mock
async def test_short_page_is_rejected_not_published() -> None:
    header, rows = _case("traditional_market", total=1393)
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)  # 1,393건 선언에 3건
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_PAGE_INCOMPLETE"):
            [i async for i in client.traditional_market.iter_file_all()]


@respx.mock
async def test_free_form_numbers_keep_the_row() -> None:
    header, rows = _case("special_street")
    rows[1]["STOR_NUMBER"] = "약 30"
    rows[1]["STRET_LT"] = "1.2km"
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(max_rps=1000) as client:
        items = [i async for i in client.special_street.iter_file_all()]
    assert len(items) == 3
    assert items[1].stor_number is None and items[1].stret_lt is None
    assert items[1].raw["STOR_NUMBER"] == "약 30"


@respx.mock
async def test_invalid_row_rejects_the_whole_file() -> None:
    header, rows = _case("special_street")
    rows[1]["REFERENCE_DATE"] = {"nested": "not a date"}
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_ROW_INVALID"):
            [i async for i in client.special_street.iter_file_all()]


@respx.mock
async def test_unknown_dataset_error_body_is_reported() -> None:
    respx.get(HEADER_URL).respond(200, json={"error": "해당 표준데이터셋이 존재하지 않습니다."})
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="존재하지 않습니다"):
            [i async for i in client.traditional_market.iter_file_all()]


@respx.mock
async def test_html_data_page_is_rejected() -> None:
    header, _ = _case("traditional_market")
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, content=b"<!doctype html><html></html>")
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_PAGE_INVALID"):
            [i async for i in client.traditional_market.iter_file_all()]


@respx.mock
async def test_page_limit_and_bounds() -> None:
    header, _ = _case("traditional_market", total=1393)
    respx.get(HEADER_URL).respond(200, json=header)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_PAGE_LIMIT"):
            [i async for i in client.traditional_market.iter_file_all(num_of_rows=500, max_pages=2)]
        with pytest.raises(ValueError, match="page bounds"):
            [i async for i in client.traditional_market.iter_file_all(num_of_rows=0)]


@respx.mock
async def test_metadata_change_during_download_is_rejected() -> None:
    header, rows = _case("traditional_market")
    changed = deepcopy(header)
    changed["tableVO"]["colNmList"] = [*header["tableVO"]["colNmList"], "INSTT_CODE"]
    respx.get(HEADER_URL).mock(
        side_effect=[httpx.Response(200, json=header), httpx.Response(200, json=changed)]
    )
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_METADATA_CHANGED"):
            [i async for i in client.traditional_market.iter_file_all()]


def test_service_without_public_transport_refuses_file() -> None:
    from datagokr.services import TraditionalMarketService

    class _Null:
        async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
            raise AssertionError

        async def aclose(self) -> None:
            pass

    with pytest.raises(RuntimeError, match="public file transport"):
        TraditionalMarketService(transport=_Null()).iter_file_pages()


@pytest.mark.parametrize(
    ("name", "pk", "key_column", "key_field"),
    [
        ("parking", "15012896", "PRKPLCE_NO", "prkplce_no"),
        ("museum_art", "15017323", "FCLTY_NM", "fclty_nm"),
        ("tourist_attraction", "15021141", "TRRSRT_NM", "trrsrt_nm"),
    ],
)
@respx.mock
async def test_parking_museum_tourist_files_are_keyless(
    monkeypatch: pytest.MonkeyPatch, name: str, pk: str, key_column: str, key_field: str,
) -> None:
    """주차장·박물관미술관·관광지도 Open API 활용신청 없이 포털 공개 파일로 받는다(2026-11-10)."""
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "must-not-be-sent")
    header, rows = _case(name)
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(api_key="also-must-not-be-sent", max_rps=1000) as client:
        items = [i async for i in getattr(client, name).iter_file_all()]

    assert [getattr(i, key_field) for i in items] == [r[key_column] for r in rows]
    assert all(i.raw[key_column] == getattr(i, key_field) for i in items)
    assert all(i.latitude is not None for i in items)
    assert respx.calls[0].request.url.params["pk"] == pk
    data = [c.request for c in respx.calls if c.request.url.path.endswith("standard.json")]
    assert data[0].url.params["publicDataPk"] == pk
    assert data[0].url.params["svcTableNm"] == header["tableVO"]["svcTableNm"]
    for call in respx.calls:
        assert "serviceKey" not in call.request.url.params


@respx.mock
async def test_parking_file_maps_numbers_and_blank_strings() -> None:
    header, rows = _case("parking")
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(max_rps=1000) as client:
        items = [i async for i in client.parking.iter_file_all()]
    first = items[0]
    assert first.prkcmprt == int(rows[0]["PRKCMPRT"])
    assert first.latitude == pytest.approx(float(rows[0]["LATITUDE"]))
    assert first.reference_date is not None
    assert rows[0]["RDNMADR"] == "" and first.rdnmadr is None


@respx.mock
async def test_parking_file_rejects_another_datasets_header() -> None:
    header, _ = _case("parking")
    header["tableVO"]["svcTableNm"] = "tn_pubr_public_trrsrt_svc"
    respx.get(HEADER_URL).respond(200, json=header)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_COLUMNS_INVALID"):
            [i async for i in client.parking.iter_file_all()]

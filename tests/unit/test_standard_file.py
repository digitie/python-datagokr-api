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
async def test_invalid_row_rejects_the_whole_file() -> None:
    header, rows = _case("special_street")
    rows[1]["STOR_NUMBER"] = "약 30"  # 특화거리 모델은 정수만 받는다
    respx.get(HEADER_URL).respond(200, json=header)
    respx.get(DATA_URL).respond(200, json=rows)
    async with DataGoKrClient(max_rps=1000) as client:
        with pytest.raises(ApiErrorResponse, match="FILE_ROW_INVALID"):
            [i async for i in client.special_street.iter_file_all()]


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

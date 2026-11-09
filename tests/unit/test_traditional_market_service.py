from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from datagokr import DataGoKrClient, PublicTraditionalMarket, get_api_catalog_entry
from datagokr.services import TRADITIONAL_MARKET_ENDPOINT, TraditionalMarketService

_FIXTURE = Path(__file__).parent / "fixtures" / "traditional_market_page.json"


class FakeTransport:
    def __init__(self, *responses: bytes) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        self.calls.append((path, params))
        return self.responses.pop(0)

    async def aclose(self) -> None:
        pass


def _page(*items: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE."},
                "body": {"items": list(items), "totalCount": len(items), "pageNo": 1},
            }
        },
        ensure_ascii=False,
    ).encode()


async def test_traditional_market_parses_recorded_official_rows() -> None:
    transport = FakeTransport(_FIXTURE.read_bytes())
    service = TraditionalMarketService(transport=transport)

    page = await service.list(page_no=1, num_of_rows=100)

    assert transport.calls == [
        (TRADITIONAL_MARKET_ENDPOINT, {"pageNo": 1, "numOfRows": 100, "type": "json"})
    ]
    assert page.total_count == 6
    names = [item.mrkt_nm for item in page.items]
    assert names == [
        "망원시장",
        "신포시장",
        "강화풍물시장",
        "운천전통시장",
        "함열시장",
        "영동전통시장",
    ]

    mangwon = page.items[0]
    assert mangwon.mrkt_type == "상설장"
    assert mangwon.rdnmadr == "서울특별시 마포구 망원로8길 7"
    assert mangwon.lnmadr == "서울특별시 마포구 망원동 486-37"
    assert mangwon.mrkt_estbl_cycle == "매일"
    assert mangwon.latitude == 37.55715742
    assert mangwon.longitude == 126.9059507
    assert mangwon.stor_number == 82
    assert mangwon.estbl_year == 2006
    assert mangwon.pblic_toilet_yn == "Y"
    assert mangwon.prkplce_yn == "Y"
    assert mangwon.phone_number == "02-335-3591"
    assert mangwon.reference_date == date(2025, 11, 10)
    # 빈 칸은 None, 원문은 raw에 그대로 남는다.
    assert mangwon.homepage_url is None
    assert mangwon.use_gcct is None
    assert mangwon.raw["mrktNm"] == "망원시장"

    ganghwa = page.items[2]
    assert ganghwa.mrkt_estbl_cycle == "2일+7일"

    # 좌표 없는 행(함열시장)과 도로명 없는 행(영동전통시장)도 버리지 않는다.
    # "전북특별차치도"는 원천 데이터의 오타를 그대로 옮긴 것이다(가공하지 않는다).
    hamyeol = page.items[4]
    assert hamyeol.latitude is None and hamyeol.longitude is None
    assert hamyeol.lnmadr == "전북특별차치도 익산시 와리 565-26"
    yeongdong = page.items[5]
    assert yeongdong.rdnmadr is None
    assert yeongdong.latitude is not None


async def test_traditional_market_keeps_rows_with_free_form_numbers() -> None:
    row = {
        "mrktNm": "표기오류시장",
        "rdnmadr": "강원특별자치도 정선군 정선읍 5일장길 1",
        "latitude": "위도미상",
        "longitude": " 128.66 ",
        "storNumber": "약 50",
        "estblYear": "1966년",
        "instt_code": "4211000",
    }
    service = TraditionalMarketService(transport=FakeTransport(_page(row)))

    page = await service.list()

    assert len(page.items) == 1
    item = page.items[0]
    assert item.latitude is None
    assert item.longitude == 128.66
    assert item.stor_number is None
    assert item.estbl_year is None
    assert item.instt_code == "4211000"
    assert item.raw["storNumber"] == "약 50"


@pytest.mark.parametrize(
    ("field", "value", "attr", "expected"),
    [
        ("latitude", "NaN", "latitude", None),
        ("latitude", "inf", "latitude", None),
        ("longitude", "1e400", "longitude", None),
        ("longitude", float("nan"), "longitude", None),
        ("latitude", 37.5, "latitude", 37.5),
        ("storNumber", 12.0, "stor_number", 12),
        ("storNumber", 12.5, "stor_number", None),
        ("storNumber", "-3", "stor_number", None),
        ("estblYear", True, "estbl_year", None),
        ("referenceDate", "20251110", "reference_date", date(2025, 11, 10)),
        ("referenceDate", "2025.11.10", "reference_date", date(2025, 11, 10)),
        ("referenceDate", "2025-11-1", "reference_date", date(2025, 11, 1)),
        ("referenceDate", " ", "reference_date", None),
        ("referenceDate", "미상", "reference_date", None),
    ],
)
async def test_traditional_market_never_drops_row_on_bad_scalar(
    field: str, value: Any, attr: str, expected: Any
) -> None:
    row = {"mrktNm": "검증시장", field: value}
    service = TraditionalMarketService(transport=FakeTransport(_page(row)))

    page = await service.list()

    assert [item.mrkt_nm for item in page.items] == ["검증시장"]
    assert getattr(page.items[0], attr) == expected


async def test_traditional_market_iter_all_walks_pages() -> None:
    first = {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "items": [{"mrktNm": "가"}, {"mrktNm": "나"}],
                "totalCount": 3,
                "pageNo": 1,
                "numOfRows": 2,
            },
        }
    }
    second = {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": [{"mrktNm": "다"}], "totalCount": 3, "pageNo": 2, "numOfRows": 2},
        }
    }
    transport = FakeTransport(
        json.dumps(first, ensure_ascii=False).encode(),
        json.dumps(second, ensure_ascii=False).encode(),
    )
    service = TraditionalMarketService(transport=transport)

    names = [item.mrkt_nm async for item in service.iter_all(num_of_rows=2)]

    assert names == ["가", "나", "다"]
    assert [params["pageNo"] for _, params in transport.calls if params] == [1, 2]


async def test_client_exposes_traditional_market_and_catalog_entry() -> None:
    async with DataGoKrClient(api_key="key") as client:
        assert isinstance(client.traditional_market, TraditionalMarketService)
        assert client.traditional_market.endpoint == TRADITIONAL_MARKET_ENDPOINT

    entry = get_api_catalog_entry("traditional_market")
    assert entry.title == "전국전통시장표준데이터"
    assert entry.endpoint == TRADITIONAL_MARKET_ENDPOINT
    assert entry.service_attr == "traditional_market"
    assert PublicTraditionalMarket.model_validate({"mrktNm": "x"}).mrkt_nm == "x"

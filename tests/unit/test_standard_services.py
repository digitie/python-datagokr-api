from __future__ import annotations

from typing import Any

import pytest

from datagokr.exceptions import ApiErrorResponse
from datagokr.services import (
    CULTURAL_FESTIVAL_ENDPOINT,
    MUSEUM_ART_GALLERY_ENDPOINT,
    PARKING_LOT_ENDPOINT,
    SPECIAL_STREET_ENDPOINT,
    TOURIST_ATTRACTION_ENDPOINT,
    CulturalFestivalService,
    MuseumArtGalleryService,
    ParkingLotService,
    SpecialStreetService,
    TouristAttractionService,
)


class FakeTransport:
    def __init__(self, *responses: bytes) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        self.calls.append((path, params))
        return self.responses.pop(0)

    def close(self) -> None:
        pass


def test_museum_art_service_parses_standard_json_response() -> None:
    transport = FakeTransport(
        """
        {
          "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
              "items": [
                {
                  "fcltyNm": "Sample Museum",
                  "fcltyType": "공립",
                  "latitude": "37.5796",
                  "longitude": "126.9769",
                  "referenceDate": "2026-05-19"
                }
              ],
              "totalCount": 1,
              "pageNo": 1,
              "numOfRows": 100
            }
          }
        }
        """
        .encode()
    )
    service = MuseumArtGalleryService(transport=transport)

    page = service.list(page_no=1, num_of_rows=100, fcltyNm="Sample")

    assert page.total_count == 1
    assert page.items[0].fclty_nm == "Sample Museum"
    assert page.items[0].latitude == 37.5796
    assert page.items[0].raw["fcltyNm"] == "Sample Museum"
    assert transport.calls[0] == (
        MUSEUM_ART_GALLERY_ENDPOINT,
        {"pageNo": 1, "numOfRows": 100, "type": "json", "fcltyNm": "Sample"},
    )


def test_parking_service_accepts_xml_response() -> None:
    transport = FakeTransport(
        b"""
        <response>
          <header><resultCode>00</resultCode><resultMsg>NORMAL_CODE</resultMsg></header>
          <body>
            <items>
              <item>
                <prkplceNo>P-1</prkplceNo>
                <prkplceNm>Central Parking</prkplceNm>
                <prkcmprt>42</prkcmprt>
              </item>
            </items>
            <totalCount>1</totalCount>
            <pageNo>1</pageNo>
            <numOfRows>100</numOfRows>
          </body>
        </response>
        """
    )
    service = ParkingLotService(transport=transport)

    page = service.list(page_no=1, num_of_rows=100, response_type="xml")

    assert page.items[0].prkplce_no == "P-1"
    assert page.items[0].prkplce_nm == "Central Parking"
    assert page.items[0].prkcmprt == 42
    assert transport.calls[0][0] == PARKING_LOT_ENDPOINT


def test_parking_service_parses_fractional_time_fields() -> None:
    # live 실측(2026-06-11, #6): addUnitTime이 '0.5' 같은 분수로 오는 row가 있다.
    transport = FakeTransport(
        b"""
        {
          "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
              "items": [
                {
                  "prkplceNo": "P-2",
                  "prkplceNm": "Fraction Parking",
                  "basicTime": "0.5",
                  "addUnitTime": "0.5",
                  "addUnitCharge": "500"
                }
              ],
              "totalCount": 1,
              "pageNo": 1,
              "numOfRows": 100
            }
          }
        }
        """
    )
    service = ParkingLotService(transport=transport)

    page = service.list(page_no=1, num_of_rows=100)

    item = page.items[0]
    assert item.basic_time == 0.5
    assert item.add_unit_time == 0.5
    assert item.add_unit_charge == 500


def test_parking_service_coerces_free_form_charge_fields() -> None:
    # live 실측(2026-06-12, #8): addUnitCharge가 '200+400' 같은 자유 표기로 오는 row가 있다.
    # 산술 평가는 의미 왜곡이므로 비숫자는 None, 원본은 raw에 보존된다.
    transport = FakeTransport(
        b"""
        {
          "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
              "items": [
                {
                  "prkplceNo": "P-3",
                  "prkplceNm": "Free Form Parking",
                  "prkcmprt": 42,
                  "basicCharge": " 500 ",
                  "addUnitCharge": "200+400",
                  "dayCmmtkt": "10000",
                  "monthCmmtkt": null
                }
              ],
              "totalCount": 1,
              "pageNo": 1,
              "numOfRows": 100
            }
          }
        }
        """
    )
    service = ParkingLotService(transport=transport)

    page = service.list(page_no=1, num_of_rows=100)

    item = page.items[0]
    assert item.add_unit_charge is None
    assert item.basic_charge == 500
    assert item.prkcmprt == 42
    assert item.day_cmmtkt == 10000
    assert item.month_cmmtkt is None
    assert item.raw["addUnitCharge"] == "200+400"


def test_iter_pages_stops_at_max_pages() -> None:
    body = b"""
    {
      "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
        "body": {
          "items": [{"trrsrtNm": "A"}, {"trrsrtNm": "B"}],
          "totalCount": 10,
          "pageNo": 1,
          "numOfRows": 2
        }
      }
    }
    """
    transport = FakeTransport(body, body)
    service = TouristAttractionService(transport=transport)

    pages = list(service.iter_pages(num_of_rows=2, max_pages=2))

    assert len(pages) == 2
    assert transport.calls[0][0] == TOURIST_ATTRACTION_ENDPOINT
    assert transport.calls[1][1]["pageNo"] == 2


def test_special_street_service_parses_standard_json_response() -> None:
    transport = FakeTransport(
        """
        {
          "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
            "body": {
              "items": [
                {
                  "stretNm": "광릉숲음식문화특화테마거리",
                  "stretIntrcn": "향토음식 기반 특화거리",
                  "rdnmadr": "경기도 남양주시 진접읍 광릉수목원로 179-19",
                  "latitude": "37.74711118",
                  "longitude": "127.1874489",
                  "stretLt": "480",
                  "storNumber": "15",
                  "appnYear": "2015",
                  "phoneNumber": "031-590-2237",
                  "institutionNm": "경기도 남양주시청 위생과",
                  "referenceDate": "2026-03-26"
                }
              ],
              "totalCount": 1,
              "pageNo": 1,
              "numOfRows": 100
            }
          }
        }
        """
        .encode()
    )
    service = SpecialStreetService(transport=transport)

    page = service.list(page_no=1, num_of_rows=100, stretNm="음식")

    item = page.items[0]
    assert item.stret_nm == "광릉숲음식문화특화테마거리"
    assert item.longitude == 127.1874489
    assert item.stret_lt == 480
    assert item.stor_number == 15
    assert item.appn_year == 2015
    assert item.raw["stretNm"] == "광릉숲음식문화특화테마거리"
    assert transport.calls[0] == (
        SPECIAL_STREET_ENDPOINT,
        {"pageNo": 1, "numOfRows": 100, "type": "json", "stretNm": "음식"},
    )


def test_api_error_raises() -> None:
    transport = FakeTransport(
        b"""
        {
          "response": {
            "header": {"resultCode": "30", "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"},
            "body": {}
          }
        }
        """
    )
    service = CulturalFestivalService(transport=transport)

    with pytest.raises(ApiErrorResponse, match="30"):
        service.list()

    assert transport.calls[0][0] == CULTURAL_FESTIVAL_ENDPOINT

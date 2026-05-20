from __future__ import annotations

from typing import Any

import pytest

from datagokr.exceptions import ApiErrorResponse
from datagokr.services import (
    CULTURAL_FESTIVAL_ENDPOINT,
    MUSEUM_ART_GALLERY_ENDPOINT,
    PARKING_LOT_ENDPOINT,
    TOURIST_ATTRACTION_ENDPOINT,
    CulturalFestivalService,
    MuseumArtGalleryService,
    ParkingLotService,
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

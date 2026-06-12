from __future__ import annotations

from typing import Any

import pytest

from datagokr.exceptions import ApiErrorResponse
from datagokr.services import FILE_DATASETS, FileDataService, get_file_dataset


class FakeTransport:
    def __init__(self, *responses: bytes) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        self.calls.append((path, params))
        return self.responses.pop(0)

    def close(self) -> None:
        pass


def test_file_data_catalog_contains_curated_candidates() -> None:
    assert set(FILE_DATASETS) == {
        "datagokr_seoul_bookstores",
        "datagokr_gyeonggi_muslim_friendly_restaurants",
        "datagokr_ansan_world_restaurants",
        "datagokr_jeju_local_restaurants",
    }

    ansan = get_file_dataset("datagokr_ansan_world_restaurants")
    assert ansan.public_data_pk == "15152605"
    assert ansan.public_data_detail_pk == "uddi:565415a5-1323-4317-8bc6-b5c914cbd7ec"
    assert ansan.endpoint_url.endswith("/15152605/v1/uddi:565415a5-1323-4317-8bc6-b5c914cbd7ec")
    assert ansan.row_count == 44


def test_file_data_service_parses_odcloud_response_and_preserves_raw() -> None:
    transport = FakeTransport(
        """
        {
          "page": 1,
          "perPage": 1,
          "totalCount": 44,
          "data": [
            {
              "가게명": "사마르칸트",
              "음식종류": "우즈베키스탄 음식",
              "주소": "경기도 안산시 단원구"
            }
          ]
        }
        """
        .encode()
    )
    service = FileDataService(transport=transport)

    page = service.ansan_world_restaurants(per_page=1, **{"가게명": "사마르칸트"})

    assert page.total_count == 44
    assert page.items[0].raw["가게명"] == "사마르칸트"
    assert page.items[0].raw["음식종류"] == "우즈베키스탄 음식"
    assert transport.calls[0] == (
        "https://api.odcloud.kr/api/15152605/v1/uddi:565415a5-1323-4317-8bc6-b5c914cbd7ec",
        {"page": 1, "perPage": 1, "가게명": "사마르칸트"},
    )


def test_file_data_service_rejects_invalid_page_size() -> None:
    service = FileDataService(transport=FakeTransport(b"{}"))

    with pytest.raises(ValueError, match="per_page"):
        service.seoul_bookstores(per_page=0)


def test_file_data_service_raises_api_error_response() -> None:
    service = FileDataService(
        transport=FakeTransport(b'{"code": "-401", "msg": "SERVICE_KEY_IS_NOT_REGISTERED"}')
    )

    with pytest.raises(ApiErrorResponse, match="-401"):
        service.jeju_local_restaurants()

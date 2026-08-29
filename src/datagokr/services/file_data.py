from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import TypeAdapter

from datagokr.config import DEFAULT_MAX_PAGE_SIZE
from datagokr.exceptions import ApiErrorResponse, UnknownDatasetError, ValidationError
from datagokr.models import PublicFileDataRecord, StandardPage
from datagokr.transport import SyncTransport

ODCLOUD_BASE_URL = "https://api.odcloud.kr/api"


@dataclass(frozen=True, slots=True)
class FileDataCatalogEntry:
    slug: str
    title: str
    provider: str
    public_data_pk: str
    public_data_detail_pk: str
    detail_url: str
    row_count: int | None = None
    update_cycle: str | None = None
    modified_on: date | None = None
    next_expected_on: date | None = None
    license_note: str | None = None
    freshness_note: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def endpoint_url(self) -> str:
        return (
            f"{ODCLOUD_BASE_URL}/{self.public_data_pk}/v1/"
            f"{self.public_data_detail_pk}"
        )


FILE_DATASETS: dict[str, FileDataCatalogEntry] = {
    "datagokr_seoul_bookstores": FileDataCatalogEntry(
        slug="datagokr_seoul_bookstores",
        title="서울특별시_책방(서점) 현황정보",
        provider="서울특별시",
        public_data_pk="15084328",
        public_data_detail_pk="uddi:d1c4d312-ae19-46bd-b850-a075d7183818",
        detail_url="https://www.data.go.kr/data/15084328/fileData.do",
        row_count=555,
        update_cycle="수시 (1회성 데이터)",
        modified_on=date(2025, 12, 2),
        license_note="제3자 권리 포함: 저작권 표시 / 공공누리 제1유형",
        freshness_note=(
            "data.go.kr는 기관 자체 URL을 가리키며, 서울 열린데이터광장 원천은 "
            "2026-06-12 확인 시 서비스 종료 안내가 함께 노출된다."
        ),
        tags=("bookstore", "seoul", "culture", "curated"),
    ),
    "datagokr_gyeonggi_muslim_friendly_restaurants": FileDataCatalogEntry(
        slug="datagokr_gyeonggi_muslim_friendly_restaurants",
        title="경기관광공사_경기도 무슬림 친화 음식점",
        provider="경기관광공사",
        public_data_pk="15099378",
        public_data_detail_pk="uddi:4dcf0fa7-1e62-47b1-b4ec-f7d605f6dee5",
        detail_url="https://www.data.go.kr/data/15099378/fileData.do",
        row_count=51,
        update_cycle="수시 (1회성 데이터)",
        modified_on=date(2025, 9, 23),
        license_note="이용허락범위 제한 없음",
        freshness_note=(
            "2024년 5월 기준 조사 자료이며 서비스 수준, 할랄 인증 여부를 "
            "보장하지 않는다는 원천 한계가 있다."
        ),
        tags=("restaurant", "muslim-friendly", "gyeonggi", "curated"),
    ),
    "datagokr_ansan_world_restaurants": FileDataCatalogEntry(
        slug="datagokr_ansan_world_restaurants",
        title="경기도 안산시_세계맛집(안산맛집)",
        provider="경기도 안산시",
        public_data_pk="15152605",
        public_data_detail_pk="uddi:565415a5-1323-4317-8bc6-b5c914cbd7ec",
        detail_url="https://www.data.go.kr/data/15152605/fileData.do",
        row_count=44,
        update_cycle="수시 (1회성 데이터)",
        modified_on=date(2025, 11, 20),
        license_note="이용허락범위 제한 없음",
        freshness_note="데이터 미수집으로 인한 공백 데이터가 존재한다는 원천 한계가 있다.",
        tags=("restaurant", "world-food", "ansan", "curated"),
    ),
    "datagokr_jeju_local_restaurants": FileDataCatalogEntry(
        slug="datagokr_jeju_local_restaurants",
        title="제주특별자치도_향토음식점지정현황",
        provider="제주특별자치도",
        public_data_pk="15043695",
        public_data_detail_pk="uddi:568145a3-53dc-4acb-8e37-947ed3efb6b4_201911221416",
        detail_url="https://www.data.go.kr/data/15043695/fileData.do?recommendDataYn=Y",
        row_count=62,
        update_cycle="연간",
        modified_on=date(2025, 11, 20),
        next_expected_on=date(2026, 11, 20),
        license_note="이용허락범위 제한 없음",
        freshness_note="연락처 휴대전화번호는 개인정보로 미공개된다.",
        tags=("restaurant", "local-food", "jeju", "curated"),
    ),
}


def get_file_dataset(slug: str) -> FileDataCatalogEntry:
    try:
        return FILE_DATASETS[slug]
    except KeyError:
        raise UnknownDatasetError(f"unknown data.go.kr file dataset: {slug}") from None


class FileDataService:
    """data.go.kr 파일데이터 자동변환 API의 raw row 서비스."""

    def __init__(self, *, transport: SyncTransport) -> None:
        self._transport = transport
        self._adapter: TypeAdapter[PublicFileDataRecord] = TypeAdapter(
            PublicFileDataRecord
        )

    def datasets(self) -> tuple[FileDataCatalogEntry, ...]:
        return tuple(FILE_DATASETS.values())

    def list(
        self,
        dataset: str | FileDataCatalogEntry,
        *,
        page_no: int = 1,
        per_page: int = 100,
        **filters: Any,
    ) -> StandardPage[PublicFileDataRecord]:
        if page_no <= 0:
            raise ValidationError("page_no must be greater than 0")
        if per_page <= 0 or per_page > DEFAULT_MAX_PAGE_SIZE:
            raise ValidationError(f"per_page must be between 1 and {DEFAULT_MAX_PAGE_SIZE}")

        entry = dataset if isinstance(dataset, FileDataCatalogEntry) else get_file_dataset(dataset)
        params = _request_params(page_no=page_no, per_page=per_page, filters=filters)
        payload = _parse_response(self._transport.get(entry.endpoint_url, params=params))
        _raise_for_error(payload)
        raw_items = _payload_items(payload)
        items = [
            self._adapter.validate_python({**raw, "raw": dict(raw)})
            for raw in raw_items
        ]
        return StandardPage[PublicFileDataRecord](
            total_count=_int_value(payload.get("totalCount"), len(items)),
            page_no=_int_value(payload.get("page"), page_no),
            num_of_rows=_int_value(payload.get("perPage"), per_page),
            items=items,
        )

    def iter_pages(
        self,
        dataset: str | FileDataCatalogEntry,
        *,
        per_page: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[StandardPage[PublicFileDataRecord]]:
        page_no = 1
        while True:
            page = self.list(dataset, page_no=page_no, per_page=per_page, **filters)
            yield page
            if not page.items:
                return
            if max_pages is not None and page_no >= max_pages:
                return
            if page.total_pages and page_no >= page.total_pages:
                return
            reached_known_end = page.total_count <= page_no * page.num_of_rows
            if len(page.items) < page.num_of_rows and reached_known_end:
                return
            page_no += 1

    def iter_all(
        self,
        dataset: str | FileDataCatalogEntry,
        *,
        per_page: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[PublicFileDataRecord]:
        for page in self.iter_pages(
            dataset, per_page=per_page, max_pages=max_pages, **filters
        ):
            yield from page.items

    def seoul_bookstores(self, **kwargs: Any) -> StandardPage[PublicFileDataRecord]:
        return self.list("datagokr_seoul_bookstores", **kwargs)

    def gyeonggi_muslim_friendly_restaurants(
        self, **kwargs: Any
    ) -> StandardPage[PublicFileDataRecord]:
        return self.list("datagokr_gyeonggi_muslim_friendly_restaurants", **kwargs)

    def ansan_world_restaurants(
        self, **kwargs: Any
    ) -> StandardPage[PublicFileDataRecord]:
        return self.list("datagokr_ansan_world_restaurants", **kwargs)

    def jeju_local_restaurants(
        self, **kwargs: Any
    ) -> StandardPage[PublicFileDataRecord]:
        return self.list("datagokr_jeju_local_restaurants", **kwargs)


def _request_params(
    *,
    page_no: int,
    per_page: int,
    filters: Mapping[str, Any],
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page_no, "perPage": per_page}
    for key, value in filters.items():
        if value not in (None, ""):
            params[key] = value
    return params


def _parse_response(content: bytes) -> Mapping[str, Any]:
    loaded = json.loads(content.decode("utf-8-sig"))
    if isinstance(loaded, Mapping):
        return loaded
    raise ApiErrorResponse(code="PARSE_ERROR", message="file data response root was not an object")


def _payload_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("data") or payload.get("items") or []
    if isinstance(rows, Mapping):
        return [rows]
    if isinstance(rows, list | tuple):
        return [row for row in rows if isinstance(row, Mapping)]
    return []


def _raise_for_error(payload: Mapping[str, Any]) -> None:
    code = _optional_str(payload.get("code") or payload.get("resultCode"))
    message = _optional_str(
        payload.get("msg") or payload.get("message") or payload.get("resultMsg")
    )
    if code in (None, "", "0", "00", "NORMAL_CODE"):
        return
    raise ApiErrorResponse(code=code or "UNKNOWN", message=message or "", payload=dict(payload))


def _int_value(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

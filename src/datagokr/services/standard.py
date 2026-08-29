from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, Generic, TypeVar

from pydantic import TypeAdapter, ValidationError

from datagokr.config import DEFAULT_MAX_PAGE_SIZE
from datagokr.exceptions import ApiErrorResponse
from datagokr.models import (
    PublicCulturalFestival,
    PublicMuseumArtGallery,
    PublicParkingLot,
    PublicSpecialStreet,
    PublicTouristAttraction,
    StandardItem,
    StandardPage,
)
from datagokr.services import pagination
from datagokr.transport import SyncTransport

MUSEUM_ART_GALLERY_ENDPOINT = "tn_pubr_public_museum_artgr_info_api"
PARKING_LOT_ENDPOINT = "tn_pubr_prkplce_info_api"
TOURIST_ATTRACTION_ENDPOINT = "tn_pubr_public_trrsrt_api"
CULTURAL_FESTIVAL_ENDPOINT = "tn_pubr_public_cltur_fstvl_api"
SPECIAL_STREET_ENDPOINT = "tn_pubr_public_area_spcliz_stret_api"

DEFAULT_MAX_PAGES = 10_000

T = TypeVar("T", bound=StandardItem)


class StandardOpenApiService(Generic[T]):
    """Generic data.go.kr standard dataset service."""

    def __init__(
        self,
        *,
        transport: SyncTransport,
        endpoint: str,
        model_type: type[T],
    ) -> None:
        self._transport = transport
        self.endpoint = endpoint
        self._model_type = model_type
        self._adapter: TypeAdapter[T] = TypeAdapter(model_type)

    def list(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 100,
        response_type: str = "json",
        **filters: Any,
    ) -> StandardPage[T]:
        if page_no <= 0:
            raise ValueError("page_no must be greater than 0")
        if num_of_rows <= 0 or num_of_rows > DEFAULT_MAX_PAGE_SIZE:
            raise ValueError(f"num_of_rows must be between 1 and {DEFAULT_MAX_PAGE_SIZE}")

        params = _request_params(
            page_no=page_no,
            num_of_rows=num_of_rows,
            response_type=response_type,
            filters=filters,
        )
        payload = pagination.parse_response(self._transport.get(self.endpoint, params=params))
        body = _response_body(payload)
        header = _response_header(payload)
        _raise_for_error(header, payload)
        raw_items = _body_items(body)
        items: list[T] = []
        for raw in raw_items:
            try:
                items.append(self._adapter.validate_python({**raw, "raw": dict(raw)}))
            except ValidationError:
                continue
        raw_total_count = pagination.first(body, "totalCount", "total_count")
        page = StandardPage[T](
            total_count=pagination.int_value(raw_total_count, len(items)),
            page_no=pagination.int_value(pagination.first(body, "pageNo", "page_no"), page_no),
            num_of_rows=pagination.int_value(
                pagination.first(body, "numOfRows", "num_of_rows"), num_of_rows
            ),
            items=items,
        )
        setattr(page, "total_count_known", raw_total_count is not None)  # noqa: B010
        return page

    def iter_pages(
        self,
        *,
        num_of_rows: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = DEFAULT_MAX_PAGES,
        **filters: Any,
    ) -> Iterator[StandardPage[T]]:
        return pagination.iter_pages(
            self.list, num_of_rows=num_of_rows, max_pages=max_pages, filters=filters
        )

    def iter_all(
        self,
        *,
        num_of_rows: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = DEFAULT_MAX_PAGES,
        **filters: Any,
    ) -> Iterator[T]:
        return pagination.iter_all(
            self.iter_pages, num_of_rows=num_of_rows, max_pages=max_pages, filters=filters
        )


class MuseumArtGalleryService(StandardOpenApiService[PublicMuseumArtGallery]):
    def __init__(self, *, transport: SyncTransport) -> None:
        super().__init__(
            transport=transport,
            endpoint=MUSEUM_ART_GALLERY_ENDPOINT,
            model_type=PublicMuseumArtGallery,
        )


class ParkingLotService(StandardOpenApiService[PublicParkingLot]):
    def __init__(self, *, transport: SyncTransport) -> None:
        super().__init__(
            transport=transport,
            endpoint=PARKING_LOT_ENDPOINT,
            model_type=PublicParkingLot,
        )


class TouristAttractionService(StandardOpenApiService[PublicTouristAttraction]):
    def __init__(self, *, transport: SyncTransport) -> None:
        super().__init__(
            transport=transport,
            endpoint=TOURIST_ATTRACTION_ENDPOINT,
            model_type=PublicTouristAttraction,
        )


class SpecialStreetService(StandardOpenApiService[PublicSpecialStreet]):
    def __init__(self, *, transport: SyncTransport) -> None:
        super().__init__(
            transport=transport,
            endpoint=SPECIAL_STREET_ENDPOINT,
            model_type=PublicSpecialStreet,
        )


class CulturalFestivalService(StandardOpenApiService[PublicCulturalFestival]):
    def __init__(self, *, transport: SyncTransport) -> None:
        super().__init__(
            transport=transport,
            endpoint=CULTURAL_FESTIVAL_ENDPOINT,
            model_type=PublicCulturalFestival,
        )


def _request_params(
    *,
    page_no: int,
    num_of_rows: int,
    response_type: str,
    filters: Mapping[str, Any],
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "type": response_type,
    }
    for key, value in filters.items():
        if value not in (None, ""):
            params[key] = value
    return params


def _response_body(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    response = payload.get("response", payload)
    if isinstance(response, Mapping):
        body = response.get("body", response)
        if isinstance(body, Mapping):
            return body
    return {}


def _response_header(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    response = payload.get("response", payload)
    if isinstance(response, Mapping) and "header" in response:
        header = response["header"]
        if isinstance(header, Mapping):
            return header
    gateway = payload.get("OpenAPI_ServiceResponse")
    if isinstance(gateway, Mapping):
        header = gateway.get("cmmMsgHeader")
        if isinstance(header, Mapping):
            return header
    return {}


def _body_items(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    items = pagination.first(body, "items", "item", "data", "row")
    if isinstance(items, Mapping):
        nested = pagination.first(items, "item", "items", "data", "row")
        if nested is not None:
            items = nested
        else:
            return [items]
    if isinstance(items, Mapping):
        return [items]
    if isinstance(items, list | tuple):
        return [item for item in items if isinstance(item, Mapping)]
    return []


def _raise_for_error(header: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    code = pagination.optional_str(
        pagination.first(header, "resultCode", "result_code", "returnReasonCode")
    )
    message = (
        pagination.optional_str(
            pagination.first(header, "resultMsg", "result_msg", "returnAuthMsg")
        )
        or ""
    )
    if code in (None, "", "00", "NORMAL_CODE"):
        return
    if code == "03":
        return
    raise ApiErrorResponse(code=str(code), message=message, payload=dict(payload))

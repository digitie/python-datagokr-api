from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import Any, Generic, TypeVar
from xml.etree import ElementTree

from pydantic import TypeAdapter

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
from datagokr.transport import SyncTransport

MUSEUM_ART_GALLERY_ENDPOINT = "tn_pubr_public_museum_artgr_info_api"
PARKING_LOT_ENDPOINT = "tn_pubr_prkplce_info_api"
TOURIST_ATTRACTION_ENDPOINT = "tn_pubr_public_trrsrt_api"
CULTURAL_FESTIVAL_ENDPOINT = "tn_pubr_public_cltur_fstvl_api"
SPECIAL_STREET_ENDPOINT = "tn_pubr_public_area_spcliz_stret_api"

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
        payload = _parse_response(self._transport.get(self.endpoint, params=params))
        body = _response_body(payload)
        header = _response_header(payload)
        _raise_for_error(header, payload)
        raw_items = _body_items(body)
        items = [self._adapter.validate_python({**raw, "raw": dict(raw)}) for raw in raw_items]
        return StandardPage[T](
            total_count=_int_value(_first(body, "totalCount", "total_count"), len(items)),
            page_no=_int_value(_first(body, "pageNo", "page_no"), page_no),
            num_of_rows=_int_value(_first(body, "numOfRows", "num_of_rows"), num_of_rows),
            items=items,
        )

    def iter_pages(
        self,
        *,
        num_of_rows: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[StandardPage[T]]:
        page_no = 1
        while True:
            page = self.list(page_no=page_no, num_of_rows=num_of_rows, **filters)
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
        *,
        num_of_rows: int = DEFAULT_MAX_PAGE_SIZE,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[T]:
        for page in self.iter_pages(num_of_rows=num_of_rows, max_pages=max_pages, **filters):
            yield from page.items


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


def _parse_response(content: bytes) -> Mapping[str, Any]:
    stripped = content.lstrip()
    if stripped.startswith((b"{", b"[")):
        loaded = json.loads(content.decode("utf-8-sig"))
        return loaded if isinstance(loaded, Mapping) else {"response": {"body": {"items": loaded}}}
    return _xml_to_mapping(content)


def _xml_to_mapping(content: bytes) -> Mapping[str, Any]:
    root = ElementTree.fromstring(content)
    return {root.tag: _element_to_value(root)}


def _element_to_value(element: ElementTree.Element) -> Any:
    children = list(element)
    text = (element.text or "").strip()
    if not children:
        return text
    grouped: dict[str, Any] = {}
    for child in children:
        value = _element_to_value(child)
        existing = grouped.get(child.tag)
        if existing is None:
            grouped[child.tag] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            grouped[child.tag] = [existing, value]
    return grouped


def _response_body(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    response = payload.get("response", payload)
    if isinstance(response, Mapping):
        body = response.get("body", response)
        if isinstance(body, Mapping):
            return body
    return {}


def _response_header(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    response = payload.get("response", payload)
    if isinstance(response, Mapping):
        header = response.get("header", {})
        if isinstance(header, Mapping):
            return header
    return {}


def _body_items(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    items = _first(body, "items", "item", "data", "row")
    if isinstance(items, Mapping):
        nested = _first(items, "item", "items", "data", "row")
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
    code = _optional_str(_first(header, "resultCode", "result_code", "returnReasonCode"))
    message = _optional_str(_first(header, "resultMsg", "result_msg", "returnAuthMsg")) or ""
    if code in (None, "", "00", "NORMAL_CODE"):
        return
    if code == "03":
        return
    raise ApiErrorResponse(code=str(code), message=message, payload=dict(payload))


def _first(raw: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


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

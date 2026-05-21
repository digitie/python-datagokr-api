from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import Any, Generic, TypeVar
from xml.etree import ElementTree

from pydantic import TypeAdapter

from datagokr.exceptions import ApiErrorResponse
from datagokr.models import (
    AgriWeatherObservationStation,
    KwaterSluiceRecord,
    OpenApiPage,
    StandardItem,
)
from datagokr.transport import SyncTransport

AGRI_WEATHER_STATION_ENDPOINT = "https://apis.data.go.kr/1390802/AgriWeather/getObsrSpotList"
KWATER_SLUICE_HOUR_ENDPOINT = (
    "https://apis.data.go.kr/B500001/dam/sluicePresentCondition/hourlist"
)
KWATER_SLUICE_TEN_MINUTE_ENDPOINT = (
    "https://apis.data.go.kr/B500001/dam/sluicePresentCondition/list"
)
KWATER_SLUICE_DAY_ENDPOINT = (
    "https://apis.data.go.kr/B500001/dam/sluicePresentCondition/daylist"
)

T = TypeVar("T", bound=StandardItem)


class DataGoKrOpenApiService(Generic[T]):
    """Generic service for non-standard data.go.kr OpenAPI list responses."""

    def __init__(
        self,
        *,
        transport: SyncTransport,
        endpoint: str,
        model_type: type[T],
        page_no_param: str = "pageNo",
        num_rows_param: str = "numOfRows",
        response_type_param: str | None = "_type",
        response_type_value: str | None = "json",
        body_item_keys: tuple[str, ...] = ("item", "items", "row", "data"),
        default_num_of_rows: int = 10,
    ) -> None:
        self._transport = transport
        self.endpoint = endpoint
        self._adapter: TypeAdapter[T] = TypeAdapter(model_type)
        self._page_no_param = page_no_param
        self._num_rows_param = num_rows_param
        self._response_type_param = response_type_param
        self._response_type_value = response_type_value
        self._body_item_keys = body_item_keys
        self._default_num_of_rows = default_num_of_rows

    def list(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int | None = None,
        **filters: Any,
    ) -> OpenApiPage[T]:
        if page_no <= 0:
            raise ValueError("page_no must be greater than 0")
        resolved_num_of_rows = num_of_rows or self._default_num_of_rows
        if resolved_num_of_rows <= 0:
            raise ValueError("num_of_rows must be greater than 0")

        params: dict[str, Any] = {
            self._page_no_param: page_no,
            self._num_rows_param: resolved_num_of_rows,
        }
        if self._response_type_param and self._response_type_value:
            params[self._response_type_param] = self._response_type_value
        for key, value in filters.items():
            if value not in (None, ""):
                params[key] = value

        payload = _parse_response(self._transport.get(self.endpoint, params=params))
        body = _response_body(payload)
        header = _response_header(payload)
        _raise_for_error(header, payload)
        raw_items = _body_items(body, item_keys=self._body_item_keys)
        items = [self._adapter.validate_python({**raw, "raw": dict(raw)}) for raw in raw_items]
        return OpenApiPage[T](
            total_count=_int_value(
                _first(body, "totalCount", "Total_Count", "total_count"),
                len(items),
            ),
            page_no=_int_value(_first(body, "pageNo", "Page_No", "page_no"), page_no),
            num_of_rows=_int_value(
                _first(body, "numOfRows", "Rcdcnt", "num_of_rows"),
                resolved_num_of_rows,
            ),
            items=items,
        )

    def iter_pages(
        self,
        *,
        num_of_rows: int | None = None,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[OpenApiPage[T]]:
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
            if len(page.items) < page.num_of_rows:
                return
            page_no += 1

    def iter_all(
        self,
        *,
        num_of_rows: int | None = None,
        max_pages: int | None = None,
        **filters: Any,
    ) -> Iterator[T]:
        for page in self.iter_pages(num_of_rows=num_of_rows, max_pages=max_pages, **filters):
            yield from page.items


class AgriWeatherService:
    """농촌진흥청 국립농업과학원 농업기상 OpenAPI facade."""

    def __init__(self, *, transport: SyncTransport) -> None:
        self.observation_stations = DataGoKrOpenApiService[AgriWeatherObservationStation](
            transport=transport,
            endpoint=AGRI_WEATHER_STATION_ENDPOINT,
            model_type=AgriWeatherObservationStation,
            page_no_param="Page_No",
            num_rows_param="Page_Size",
            response_type_param=None,
            response_type_value=None,
            body_item_keys=("item", "items", "row"),
            default_num_of_rows=10,
        )

    def station_list(
        self,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        obsr_spot_nm: str | None = None,
        obsr_spot_code: str | None = None,
        do_se_code: str | None = None,
        mgc_code: str | None = None,
        obsr_begin_datetm: str | None = None,
    ) -> OpenApiPage[AgriWeatherObservationStation]:
        return self.observation_stations.list(
            page_no=page_no,
            num_of_rows=num_of_rows,
            Obsr_Spot_Nm=obsr_spot_nm,
            Obsr_Spot_Code=obsr_spot_code,
            Do_Se_Code=do_se_code,
            Mgc_Code=mgc_code,
            Obsr_Begin_Datetm=obsr_begin_datetm,
        )


class KwaterSluiceService:
    """한국수자원공사 수문 운영 정보 OpenAPI facade."""

    def __init__(self, *, transport: SyncTransport) -> None:
        self.hourly = DataGoKrOpenApiService[KwaterSluiceRecord](
            transport=transport,
            endpoint=KWATER_SLUICE_HOUR_ENDPOINT,
            model_type=KwaterSluiceRecord,
        )
        self.ten_minutes = DataGoKrOpenApiService[KwaterSluiceRecord](
            transport=transport,
            endpoint=KWATER_SLUICE_TEN_MINUTE_ENDPOINT,
            model_type=KwaterSluiceRecord,
        )
        self.daily = DataGoKrOpenApiService[KwaterSluiceRecord](
            transport=transport,
            endpoint=KWATER_SLUICE_DAY_ENDPOINT,
            model_type=KwaterSluiceRecord,
        )

    def hour_list(
        self,
        *,
        damcode: str,
        stdt: str,
        eddt: str,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> OpenApiPage[KwaterSluiceRecord]:
        page = self.hourly.list(
            page_no=page_no,
            num_of_rows=num_of_rows,
            damcode=damcode,
            stdt=stdt,
            eddt=eddt,
        )
        return _with_damcode(page, damcode)


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
        body = response.get("body") or response.get("Body") or response
        if isinstance(body, Mapping):
            return body
    return {}


def _response_header(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    response = payload.get("response", payload)
    if isinstance(response, Mapping):
        header = response.get("header") or response.get("Header") or {}
        if isinstance(header, Mapping):
            return header
    return {}


def _body_items(body: Mapping[str, Any], *, item_keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
    items = _first(body, *item_keys)
    if isinstance(items, Mapping):
        nested = _first(items, *item_keys)
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
    code = _optional_str(
        _first(header, "resultCode", "Result_Code", "result_code", "returnReasonCode")
    )
    message = _optional_str(
        _first(header, "resultMsg", "Result_Msg", "result_msg", "returnAuthMsg")
    ) or ""
    if code in (None, "", "00", "200", "NORMAL_CODE"):
        return
    raise ApiErrorResponse(code=str(code), message=message, payload=dict(payload))


def _with_damcode(
    page: OpenApiPage[KwaterSluiceRecord],
    damcode: str,
) -> OpenApiPage[KwaterSluiceRecord]:
    for item in page.items:
        if item.damcode is None:
            item.damcode = damcode
    return page


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

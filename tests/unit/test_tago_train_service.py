from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest

from datagokr import DataGoKrClient, TagoTrainService
from datagokr.exceptions import ApiErrorResponse, ResponseParseError
from datagokr.services.openapi import (
    TRAIN_CITY_ENDPOINT,
    TRAIN_CLASS_ENDPOINT,
    TRAIN_STATION_ENDPOINT,
    TRAIN_TIMETABLE_ENDPOINT,
)


class FakeTransport:
    def __init__(self, *payloads: bytes) -> None:
        self.payloads = list(payloads)
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        self.calls.append((path, params))
        return self.payloads.pop(0)

    async def aclose(self) -> None:
        pass


def payload(items: object, **metadata: object) -> bytes:
    return json.dumps({"response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": {"item": items}, **metadata},
    }}).encode()


async def test_reference_endpoints_and_lowercase_fields() -> None:
    transport = FakeTransport(
        payload([{"citycode": 11, "cityname": "서울특별시"}]),
        payload({"vehiclekndid": "00", "vehiclekndnm": "KTX"}),
        payload([{"nodeid": "NAT010000", "nodename": "서울"}], totalCount=1),
    )
    service = TagoTrainService(transport=transport)
    cities = await service.city_list()
    classes = await service.class_list()
    stations = await service.station_list(city_code="11", num_of_rows=100)
    assert cities.items[0].city_code == "11"
    assert classes.items[0].grade_id == "00"
    assert stations.items[0].station_id == "NAT010000"
    assert stations.items[0].station_name == "서울"
    assert transport.calls == [
        (TRAIN_CITY_ENDPOINT, {"_type": "json"}),
        (TRAIN_CLASS_ENDPOINT, {"_type": "json"}),
        (TRAIN_STATION_ENDPOINT, {
            "pageNo": 1, "numOfRows": 100, "_type": "json", "cityCode": "11",
        }),
    ]


async def test_timetable_preserves_midnight_numbers_and_fares() -> None:
    raw = {"trainno": 123, "traingradename": "KTX", "depplacename": "서울",
           "arrplacename": "부산", "depplandtime": 20260927235000,
           "arrplandtime": 20260928021000, "adultcharge": "59800"}
    transport = FakeTransport(payload(raw, totalCount=2, pageNo=2, numOfRows=1))
    page = await TagoTrainService(transport=transport).timetable_list(
        departure_station_id="NAT010000", arrival_station_id="NAT014445",
        departure_date=date(2026, 9, 27), train_grade_code="00", page_no=2, num_of_rows=1,
    )
    assert page.total_count == 2
    assert page.page_no == 2
    assert page.items[0].dep_planned_time == "20260927235000"
    assert page.items[0].arr_planned_time == "20260928021000"
    assert page.items[0].adult_charge == 59800
    assert page.items[0].train_number == "123"
    assert page.items[0].raw == raw
    assert transport.calls == [(TRAIN_TIMETABLE_ENDPOINT, {
        "pageNo": 2, "numOfRows": 1, "_type": "json", "depPlaceId": "NAT010000",
        "arrPlaceId": "NAT014445", "depPlandTime": "20260927", "trainGradeCode": "00",
    })]


async def test_station_iterator_preserves_city_filter_and_page_limit() -> None:
    transport = FakeTransport(
        payload({"nodeid": "A", "nodename": "가"}, totalCount=3, pageNo=1, numOfRows=1),
        payload({"nodeid": "B", "nodename": "나"}, totalCount=3, pageNo=2, numOfRows=1),
    )
    rows = [row async for row in TagoTrainService(transport=transport).iter_stations(
        city_code="11", num_of_rows=1, max_pages=2,
    )]
    assert [row.station_id for row in rows] == ["A", "B"]
    assert [params for _, params in transport.calls] == [
        {"pageNo": page, "numOfRows": 1, "_type": "json", "cityCode": "11"}
        for page in (1, 2)
    ]


@pytest.mark.parametrize("value", [
    "20260230", "2026-09-27", "\uff12\uff10\uff12\uff16\uff10\uff19\uff12\uff17",
    datetime(2026, 9, 27),
])
async def test_invalid_departure_date_does_not_call_provider(value: date | str) -> None:
    transport = FakeTransport()
    with pytest.raises(ValueError):
        await TagoTrainService(transport=transport).timetable_list(
            departure_station_id="A", arrival_station_id="B", departure_date=value,
        )
    assert transport.calls == []


async def test_empty_required_identifiers_do_not_call_provider() -> None:
    transport = FakeTransport()
    service = TagoTrainService(transport=transport)
    with pytest.raises(ValueError):
        await service.station_list(city_code=" ")
    with pytest.raises(ValueError):
        service.iter_stations(city_code="")
    with pytest.raises(ValueError):
        await service.timetable_list(
            departure_station_id=" ", arrival_station_id="B", departure_date="20260927",
        )
    assert transport.calls == []


@pytest.mark.parametrize("method", ["city", "class", "station", "timetable"])
async def test_authentication_failure_is_not_empty_data(method: str) -> None:
    transport = FakeTransport(b'<OpenAPI_ServiceResponse><cmmMsgHeader>'
        b'<returnReasonCode>30</returnReasonCode><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>'
        b'</cmmMsgHeader></OpenAPI_ServiceResponse>')
    service = TagoTrainService(transport=transport)
    with pytest.raises(ApiErrorResponse, match="30"):
        if method == "city":
            await service.city_list()
        elif method == "class":
            await service.class_list()
        elif method == "station":
            await service.station_list(city_code="11")
        else:
            await service.timetable_list(
                departure_station_id="A", arrival_station_id="B", departure_date="20260927",
            )


async def test_normal_empty_response_and_optional_filter() -> None:
    transport = FakeTransport(payload([], totalCount=0))
    page = await TagoTrainService(transport=transport).timetable_list(
        departure_station_id="A", arrival_station_id="B", departure_date="20260927",
    )
    assert page.items == []
    assert page.total_count == 0
    assert "trainGradeCode" not in (transport.calls[0][1] or {})


async def test_public_client_uses_shared_transport_and_closes() -> None:
    client = DataGoKrClient(api_key="unit-test-not-a-real-key")
    assert isinstance(client.train, TagoTrainService)
    assert client.train._transport is client.express_bus._transport
    await client.aclose()
    assert client.closed


async def call_service(service: TagoTrainService, method: str) -> Any:
    if method == "city":
        return await service.city_list()
    if method == "class":
        return await service.class_list()
    if method == "station":
        return await service.station_list(city_code="11")
    return await service.timetable_list(
        departure_station_id="A", arrival_station_id="B", departure_date="20260927",
    )


@pytest.mark.parametrize("method", ["city", "class", "station", "timetable"])
@pytest.mark.parametrize("empty", [None, "", {}, []])
async def test_empty_item_wrappers_are_not_phantom_rows(method: str, empty: object) -> None:
    transport = FakeTransport(payload(empty, totalCount=0))
    page = await call_service(TagoTrainService(transport=transport), method)
    assert page.items == []
    assert page.total_count == 0
    assert len(transport.calls) == 1


async def test_empty_xml_item_stops_iterator_after_one_call() -> None:
    transport = FakeTransport(b'<response><header><resultCode>00</resultCode></header>'
        b'<body><items><item/></items><totalCount>0</totalCount></body></response>')
    iterator = TagoTrainService(transport=transport).iter_stations(city_code="11")
    rows = [row async for row in iterator]
    assert rows == []
    assert len(transport.calls) == 1


@pytest.mark.parametrize("method", ["city", "class", "station", "timetable"])
@pytest.mark.parametrize("raw", [
    {}, {"error": "temporarily unavailable"}, {"response": {}},
    {"response": {"header": {"resultMsg": "OK"}, "body": {"items": ""}}},
    {"response": {"header": {"resultCode": "00"}}},
    {"response": {"header": {"resultCode": "00"}, "body": {}}},
])
async def test_malformed_envelopes_fail_closed(method: str, raw: object) -> None:
    transport = FakeTransport(json.dumps(raw).encode())
    with pytest.raises(ResponseParseError):
        await call_service(TagoTrainService(transport=transport), method)


@pytest.mark.parametrize("items,count", [
    ({"nodeid": "A"}, 0), ([{}], 1), ([None], 1), ("bad", 1),
    ([], True), ([], -1), ([], 1.5), ([], "bad"),
])
async def test_invalid_items_and_counts_fail_closed(items: object, count: object) -> None:
    transport = FakeTransport(payload(items, totalCount=count))
    with pytest.raises(ResponseParseError):
        await TagoTrainService(transport=transport).station_list(city_code="11")


async def test_unpaged_count_mismatch_is_not_a_complete_reference_list() -> None:
    transport = FakeTransport(payload([], totalCount=3))
    with pytest.raises(ResponseParseError):
        await TagoTrainService(transport=transport).city_list()


@pytest.mark.parametrize("method", ["city", "class", "station", "timetable"])
async def test_explicit_no_data_code_is_empty_without_body(method: str) -> None:
    transport = FakeTransport(b'{"response":{"header":{"resultCode":"03"}}}')
    page = await call_service(TagoTrainService(transport=transport), method)
    assert page.items == []
    assert page.total_count == 0


async def test_no_data_code_with_positive_count_fails_closed() -> None:
    transport = FakeTransport(b'{"response":{"header":{"resultCode":"03"},'
        b'"body":{"totalCount":1}}}')
    with pytest.raises(ResponseParseError):
        await TagoTrainService(transport=transport).city_list()


@pytest.mark.parametrize("value", [True, False, -100, "-100"])
async def test_invalid_fares_do_not_become_valid_prices(value: object) -> None:
    from pydantic import ValidationError

    transport = FakeTransport(payload({"trainno": "123", "adultcharge": value}, totalCount=1))
    with pytest.raises(ValidationError):
        await call_service(TagoTrainService(transport=transport), "timetable")


@pytest.mark.parametrize("year,expected", [(1, "00010101"), (999, "09990101"), (2026, "20260101")])
async def test_date_objects_are_always_eight_ascii_digits(year: int, expected: str) -> None:
    transport = FakeTransport(payload([], totalCount=0))
    await TagoTrainService(transport=transport).timetable_list(
        departure_station_id="A", arrival_station_id="B", departure_date=date(year, 1, 1),
    )
    assert (transport.calls[0][1] or {})["depPlandTime"] == expected

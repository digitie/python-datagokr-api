from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest

from datagokr import DataGoKrClient, TagoTrainService
from datagokr.exceptions import ApiErrorResponse
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

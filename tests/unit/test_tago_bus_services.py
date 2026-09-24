from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from datagokr import DataGoKrClient
from datagokr.exceptions import ApiErrorResponse
from datagokr.services import TagoExpressBusService, TagoIntercityBusService
from datagokr.services.openapi import (
    EXPRESS_BUS_CITY_ENDPOINT,
    EXPRESS_BUS_CLASS_ENDPOINT,
    EXPRESS_BUS_TERMINAL_ENDPOINT,
    EXPRESS_BUS_TIMETABLE_ENDPOINT,
    INTERCITY_BUS_TERMINAL_ENDPOINT,
    INTERCITY_BUS_TIMETABLE_ENDPOINT,
)


class FakeTransport:
    def __init__(self, *responses: bytes) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        self.calls.append((path, params))
        return self.responses.pop(0)

    async def aclose(self) -> None:
        pass


def _response(items: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {
                    "pageNo": 1,
                    "numOfRows": 10,
                    "totalCount": len(items),
                    "items": {"item": items},
                },
            }
        }
    ).encode()


async def test_express_bus_reference_lists_are_typed_and_paginated() -> None:
    transport = FakeTransport(
        _response([{"terminalId": "NAEK010", "terminalNm": "서울경부"}]),
        _response([{"citycode": "110", "cityname": "서울"}]),
        _response([{"gradeId": "1", "gradeNm": "프리미엄"}]),
    )
    service = TagoExpressBusService(transport=transport)

    terminals = await service.terminal_list(terminal_name="서울", num_of_rows=10)
    cities = await service.city_list(num_of_rows=10)
    classes = await service.class_list(num_of_rows=10)

    assert terminals.total_count == 1
    assert terminals.items[0].terminal_id == "NAEK010"
    assert cities.items[0].city_code == "110"
    assert classes.items[0].grade_name == "프리미엄"
    assert transport.calls == [
        (
            EXPRESS_BUS_TERMINAL_ENDPOINT,
            {"pageNo": 1, "numOfRows": 10, "_type": "json", "terminalNm": "서울"},
        ),
        (EXPRESS_BUS_CITY_ENDPOINT, {"pageNo": 1, "numOfRows": 10, "_type": "json"}),
        (EXPRESS_BUS_CLASS_ENDPOINT, {"pageNo": 1, "numOfRows": 10, "_type": "json"}),
    ]


async def test_express_bus_timetable_serializes_typed_date_and_response() -> None:
    transport = FakeTransport(
        _response(
            [
                {
                    "routeId": "R001",
                    "depPlaceNm": "서울경부",
                    "arrPlaceNm": "부산",
                    "depPlandTime": "20260925060000",
                    "arrPlandTime": "20260925094000",
                    "gradeNm": "우등",
                    "adultCharge": "38000",
                }
            ]
        )
    )
    service = TagoExpressBusService(transport=transport)

    page = await service.timetable_list(
        departure_terminal_id="NAEK010",
        arrival_terminal_id="NAEK020",
        departure_date=date(2026, 9, 25),
    )

    assert page.items[0].adult_charge == 38000
    assert page.items[0].dep_place_name == "서울경부"
    assert transport.calls == [
        (
            EXPRESS_BUS_TIMETABLE_ENDPOINT,
            {
                "pageNo": 1,
                "numOfRows": 10,
                "_type": "json",
                "depTerminalId": "NAEK010",
                "arrTerminalId": "NAEK020",
                "depPlandTime": "20260925",
            },
        )
    ]


async def test_intercity_bus_uses_its_own_tago_endpoints() -> None:
    transport = FakeTransport(
        _response([{"terminalId": "123", "terminalNm": "강릉"}]),
        _response([]),
    )
    service = TagoIntercityBusService(transport=transport)

    terminals = await service.terminal_list()
    page = await service.timetable_list(
        departure_terminal_id="123",
        arrival_terminal_id="456",
        departure_date="20260925",
        num_of_rows=20,
    )

    assert terminals.items[0].terminal_name == "강릉"
    assert not page.items
    assert transport.calls[0][0] == INTERCITY_BUS_TERMINAL_ENDPOINT
    assert transport.calls[1] == (
        INTERCITY_BUS_TIMETABLE_ENDPOINT,
        {
            "pageNo": 1,
            "numOfRows": 20,
            "_type": "json",
            "depTerminalId": "123",
            "arrTerminalId": "456",
            "depPlandTime": "20260925",
        },
    )


async def test_tago_error_envelope_and_invalid_date_are_explicit() -> None:
    transport = FakeTransport(
        b'{"response":{"header":{"resultCode":"22","resultMsg":"LIMITED"}}}'
    )
    service = TagoExpressBusService(transport=transport)

    with pytest.raises(ApiErrorResponse, match="22: LIMITED"):
        await service.city_list()
    with pytest.raises(ValueError, match="departure_date"):
        await service.timetable_list(
            departure_terminal_id="A",
            arrival_terminal_id="B",
            departure_date="2026-09-25",
        )


async def test_client_exposes_both_tago_bus_services() -> None:
    client = DataGoKrClient(api_key="test-secret")

    assert isinstance(client.express_bus, TagoExpressBusService)
    assert isinstance(client.intercity_bus, TagoIntercityBusService)

    await client.aclose()

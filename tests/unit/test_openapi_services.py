from __future__ import annotations

from typing import Any

from datagokr.services import AgriWeatherService, KwaterSluiceService
from datagokr.services.openapi import (
    AGRI_WEATHER_STATION_ENDPOINT,
    KWATER_SLUICE_HOUR_ENDPOINT,
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


def test_agri_weather_station_list_parses_xml_response() -> None:
    transport = FakeTransport(
        """
        <response>
          <header>
            <Result_Code>200</Result_Code>
            <Result_Msg>OK</Result_Msg>
          </header>
          <body>
            <Rcdcnt>10</Rcdcnt>
            <Page_No>1</Page_No>
            <Total_Count>1</Total_Count>
            <items>
              <item>
                <No>1</No>
                <Obsr_Spot_Code>542805A001</Obsr_Spot_Code>
                <Obsr_Spot_Nm>구례군 구례읍</Obsr_Spot_Nm>
                <Instl_La>35.1973055576348</Instl_La>
                <Instl_Lo>127.4609219654052</Instl_Lo>
                <Instl_Al>38</Instl_Al>
                <Instl_Adres>전라남도 구례군 구례읍 동산1길 32</Instl_Adres>
                <Obsr_Begin_Datetm>2016-05-04</Obsr_Begin_Datetm>
              </item>
            </items>
          </body>
        </response>
        """.encode()
    )
    service = AgriWeatherService(transport=transport)

    page = service.station_list(num_of_rows=10, obsr_spot_nm="구례")

    assert page.total_count == 1
    assert page.items[0].obsr_spot_code == "542805A001"
    assert page.items[0].instl_la == 35.1973055576348
    assert page.items[0].raw["Obsr_Spot_Nm"] == "구례군 구례읍"
    assert transport.calls[0] == (
        AGRI_WEATHER_STATION_ENDPOINT,
        {"Page_No": 1, "Page_Size": 10, "Obsr_Spot_Nm": "구례"},
    )


def test_kwater_sluice_hour_list_parses_json_response() -> None:
    transport = FakeTransport(
        """
        {
          "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {
              "items": {
                "item": [
                  {
                    "obsrdt": "10-01 01시",
                    "lowlevel": "0.74",
                    "rf": "0.000",
                    "inflowqy": "236.038",
                    "totdcwtrqy": "108.649",
                    "rsvwtqy": "296.377",
                    "rsvwtrt": "96.5"
                  }
                ]
              },
              "totalCount": 1,
              "pageNo": 1,
              "numOfRows": 10
            }
          }
        }
        """
        .encode()
    )
    service = KwaterSluiceService(transport=transport)

    page = service.hour_list(
        damcode="2022510",
        stdt="2018-10-01",
        eddt="2018-10-01",
        num_of_rows=10,
    )

    assert page.total_count == 1
    assert page.items[0].damcode == "2022510"
    assert page.items[0].rsvwtrt == 96.5
    assert transport.calls[0] == (
        KWATER_SLUICE_HOUR_ENDPOINT,
        {
            "pageNo": 1,
            "numOfRows": 10,
            "_type": "json",
            "damcode": "2022510",
            "stdt": "2018-10-01",
            "eddt": "2018-10-01",
        },
    )

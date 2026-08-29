"""디버그 UI 등에서 쓰는 data.go.kr API 카탈로그.

`DataGoKrClient.debug_fetch()`와 `examples/streamlit_debug_ui.py`는 이 모듈의
`get_api_catalog()`/`get_api_catalog_entry()`만으로 요청 폼을 그리고 실행을
라우팅한다 — 파라미터별/함수명별 `if ... elif ...` 분기는 두지 않는다. 새 API
표면을 추가할 때는 `_CATALOG_ROWS`에 항목을 하나 더한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from urllib.parse import quote

from datagokr.services.file_data import FILE_DATASETS
from datagokr.services.openapi import (
    AGRI_WEATHER_STATION_ENDPOINT,
    KWATER_SLUICE_DAY_ENDPOINT,
    KWATER_SLUICE_HOUR_ENDPOINT,
    KWATER_SLUICE_TEN_MINUTE_ENDPOINT,
)
from datagokr.services.standard import (
    CULTURAL_FESTIVAL_ENDPOINT,
    MUSEUM_ART_GALLERY_ENDPOINT,
    PARKING_LOT_ENDPOINT,
    SPECIAL_STREET_ENDPOINT,
    TOURIST_ATTRACTION_ENDPOINT,
)

SERVICE_KEY_PARAM: Final = "serviceKey"
SERVICE_KEY_ENV_NAMES: Final[tuple[str, ...]] = ("DATA_GO_KR_SERVICE_KEY",)

_DATA_GO_KR_SEARCH_URL = "https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword={query}"


def _search_url(title: str) -> str:
    """제목으로 data.go.kr 데이터셋 검색 결과 페이지 URL을 만듭니다.

    표준데이터/개별 OpenAPI는 저장소에 실제 `data.go.kr` 게시물 번호가 없어,
    잘못된 번호를 지어내는 대신 항상 유효한 검색 링크를 서비스키 발급 버튼에
    연결한다.
    """

    return _DATA_GO_KR_SEARCH_URL.format(query=quote(title))


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """디버그 UI 요청 폼에서 위젯 하나를 자동 생성하기 위한 파라미터 명세."""

    name: str
    required: bool
    label: str = ""
    help: str = ""
    kind: str = "text"  # "text" | "int" | "float" | "enum"
    choices: tuple[str, ...] = ()
    default: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            object.__setattr__(self, "label", self.name)


@dataclass(frozen=True, slots=True)
class ApiCatalogEntry:
    """디버그 UI가 API 하나를 렌더링/실행하는 데 필요한 모든 메타데이터."""

    key: str
    """카탈로그 전역에서 유일한 식별자. `DataGoKrClient.debug_fetch()`의 1번 인자."""

    data_source: str
    """사이드바 1단계(Data source) 선택에 쓰는 그룹 이름."""

    title: str
    """데이터셋/서비스 공식 명칭."""

    description_lines: tuple[str, str]
    """사이드바 캡션 2줄: (무엇을 하는 API인지, 어떤 데이터를 반환하는지)."""

    endpoint: str
    """실제로 호출하는 경로 또는 절대 URL."""

    service_attr: str
    """`DataGoKrClient` 인스턴스에서 서비스 객체까지의 점(.) 구분 속성 경로."""

    list_method: str = "list"
    """서비스 객체에서 호출할 페이징 조회 메서드 이름."""

    bound_args: tuple[tuple[str, object], ...] = ()
    """호출마다 고정으로 넘길 키워드 인자(예: file_data의 `dataset` slug)."""

    required_params: tuple[ParamSpec, ...] = ()
    optional_params: tuple[ParamSpec, ...] = ()

    page_no_wire_param: str = "pageNo"
    """실제 요청 URL에 실리는 페이지 번호 쿼리 파라미터명(표준과 다르면 표시)."""

    num_rows_wire_param: str = "numOfRows"
    """실제 요청 URL에 실리는 페이지당 행 수 쿼리 파라미터명(표준과 다르면 표시)."""

    num_rows_kwarg: str = "num_of_rows"
    """서비스 메서드 호출 시 페이지당 행 수를 넘기는 Python 키워드 인자 이름."""

    default_num_of_rows: int = 10

    supports_response_type: bool = True
    response_type_param: str = "type"
    response_type_choices: tuple[str, ...] = ("json", "xml")

    service_key_param: str = SERVICE_KEY_PARAM
    service_key_env_names: tuple[str, ...] = SERVICE_KEY_ENV_NAMES
    service_key_url: str = ""

    @property
    def label(self) -> str:
        return f"{self.title} ({self.key})"


def _std(
    key: str,
    *,
    title: str,
    description_lines: tuple[str, str],
    endpoint: str,
    service_attr: str,
) -> ApiCatalogEntry:
    """표준데이터 5종처럼 파일링/응답형식이 균일한 항목을 위한 축약 생성자."""

    return ApiCatalogEntry(
        key=key,
        data_source="표준 공공시설 API",
        title=title,
        description_lines=description_lines,
        endpoint=endpoint,
        service_attr=service_attr,
        default_num_of_rows=100,
        service_key_url=_search_url(title),
    )


def _file_data(slug: str) -> ApiCatalogEntry:
    entry = FILE_DATASETS[slug]
    return ApiCatalogEntry(
        key=f"file_data:{slug}",
        data_source="파일데이터 (odcloud)",
        title=entry.title,
        description_lines=(
            f"{entry.provider}가 제공하는 '{entry.title}' 원본 row를 odcloud 파일데이터 "
            "자동변환 API로 조회합니다.",
            "리스트 응답이며 각 항목은 원본 컬럼을 그대로 raw 딕셔너리로 보존합니다.",
        ),
        endpoint=entry.endpoint_url,
        service_attr="file_data",
        bound_args=(("dataset", slug),),
        num_rows_kwarg="per_page",
        default_num_of_rows=min(entry.row_count or 100, 100),
        supports_response_type=False,
        service_key_url=entry.detail_url,
    )


def _kwater(
    key: str,
    *,
    title: str,
    granularity: str,
    endpoint: str,
    service_attr: str,
) -> ApiCatalogEntry:
    return ApiCatalogEntry(
        key=key,
        data_source="K-water 수문 운영 정보",
        title=title,
        description_lines=(
            f"지정한 댐 코드(damcode)와 기간(stdt~eddt)의 {granularity} 단위 수문 운영 "
            "데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 저수위, 강우량, 유입량, 총방류량, 저수율 등을 "
            "포함합니다.",
        ),
        endpoint=endpoint,
        service_attr=service_attr,
        required_params=(
            ParamSpec("damcode", required=True, help="한국수자원공사 댐 코드입니다."),
            ParamSpec("stdt", required=True, help="조회 시작일(예: 2018-10-01)입니다."),
            ParamSpec("eddt", required=True, help="조회 종료일(예: 2018-10-01)입니다."),
        ),
        service_key_url=_search_url("한국수자원공사 댐 방류 및 수문 운영 정보"),
    )


_CATALOG_ROWS: Final[tuple[ApiCatalogEntry, ...]] = (
    _std(
        "museum_art",
        title="전국박물관미술관정보표준데이터",
        description_lines=(
            "전국 박물관·미술관의 위치, 운영시간, 요금 등 표준 데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 시설명, 주소, 위경도, 운영시간, 요금 등을 포함합니다.",
        ),
        endpoint=MUSEUM_ART_GALLERY_ENDPOINT,
        service_attr="museum_art",
    ),
    _std(
        "parking",
        title="전국주차장정보표준데이터",
        description_lines=(
            "전국 공영·민영 주차장의 위치와 요금 체계 표준 데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 주차장명, 구획수, 기본요금, 운영시간 등을 포함합니다.",
        ),
        endpoint=PARKING_LOT_ENDPOINT,
        service_attr="parking",
    ),
    _std(
        "tourist_attraction",
        title="전국관광지정보표준데이터",
        description_lines=(
            "전국 관광지의 위치와 편의시설 표준 데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 관광지명, 주소, 위경도, 편의시설 정보 등을 포함합니다.",
        ),
        endpoint=TOURIST_ATTRACTION_ENDPOINT,
        service_attr="tourist_attraction",
    ),
    _std(
        "festival",
        title="전국문화축제표준데이터",
        description_lines=(
            "전국 문화축제의 개최 기간과 주관/후원 기관 표준 데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 축제명, 개최기간, 주관기관, 위치 정보 등을 포함합니다.",
        ),
        endpoint=CULTURAL_FESTIVAL_ENDPOINT,
        service_attr="festival",
    ),
    _std(
        "special_street",
        title="전국지역특화거리표준데이터",
        description_lines=(
            "전국 지역특화거리(테마거리)의 위치와 규모 표준 데이터를 조회합니다.",
            "리스트 응답이며 각 항목은 거리명, 주소, 위경도, 점포수, 지정연도 등을 포함합니다.",
        ),
        endpoint=SPECIAL_STREET_ENDPOINT,
        service_attr="special_street",
    ),
    _file_data("datagokr_seoul_bookstores"),
    _file_data("datagokr_gyeonggi_muslim_friendly_restaurants"),
    _file_data("datagokr_ansan_world_restaurants"),
    _file_data("datagokr_jeju_local_restaurants"),
    ApiCatalogEntry(
        key="agri_weather:station_list",
        data_source="농업기상 관측정보",
        title="농업기상 관측지점 상세정보",
        description_lines=(
            "농촌진흥청 국립농업과학원 농업기상 관측지점의 위치와 설치 정보를 조회합니다.",
            "리스트 응답이며 각 항목은 관측지점명, 코드, 설치 위경도·고도, 설치일자 등을 "
            "포함합니다.",
        ),
        endpoint=AGRI_WEATHER_STATION_ENDPOINT,
        service_attr="agri_weather.observation_stations",
        optional_params=(
            ParamSpec("Obsr_Spot_Nm", required=False, help="관측지점명(부분 일치)입니다."),
            ParamSpec("Obsr_Spot_Code", required=False, help="관측지점 코드입니다."),
            ParamSpec("Do_Se_Code", required=False, help="시도 코드입니다."),
            ParamSpec("Mgc_Code", required=False, help="시군구 코드입니다."),
            ParamSpec(
                "Obsr_Begin_Datetm",
                required=False,
                help="관측 시작일자(YYYY-MM-DD)입니다.",
            ),
        ),
        # 이 OpenAPI는 표준 pageNo/numOfRows 대신 Page_No/Page_Size를 쓴다.
        page_no_wire_param="Page_No",
        num_rows_wire_param="Page_Size",
        default_num_of_rows=10,
        supports_response_type=False,
        service_key_url=_search_url("농업기상 관측지점 상세정보"),
    ),
    _kwater(
        "kwater_sluice:hourly",
        title="한국수자원공사 수문 운영 정보 (시간자료)",
        granularity="시간",
        endpoint=KWATER_SLUICE_HOUR_ENDPOINT,
        service_attr="kwater_sluice.hourly",
    ),
    _kwater(
        "kwater_sluice:ten_minutes",
        title="한국수자원공사 수문 운영 정보 (10분자료)",
        granularity="10분",
        endpoint=KWATER_SLUICE_TEN_MINUTE_ENDPOINT,
        service_attr="kwater_sluice.ten_minutes",
    ),
    _kwater(
        "kwater_sluice:daily",
        title="한국수자원공사 수문 운영 정보 (일자료)",
        granularity="일",
        endpoint=KWATER_SLUICE_DAY_ENDPOINT,
        service_attr="kwater_sluice.daily",
    ),
)

CATALOG_BY_KEY: Final[dict[str, ApiCatalogEntry]] = {row.key: row for row in _CATALOG_ROWS}


def get_api_catalog() -> tuple[ApiCatalogEntry, ...]:
    """Streamlit 디버그 UI 등에서 쓰는 전체 API 카탈로그를 반환합니다."""

    return _CATALOG_ROWS


def get_api_catalog_entry(key: str) -> ApiCatalogEntry:
    """카탈로그 key로 API 항목 하나를 반환합니다."""

    try:
        return CATALOG_BY_KEY[key]
    except KeyError as exc:
        known = ", ".join(sorted(CATALOG_BY_KEY))
        raise KeyError(f"unknown datagokr API catalog key: {key!r}; known keys: {known}") from exc


__all__ = [
    "CATALOG_BY_KEY",
    "SERVICE_KEY_ENV_NAMES",
    "SERVICE_KEY_PARAM",
    "ApiCatalogEntry",
    "ParamSpec",
    "get_api_catalog",
    "get_api_catalog_entry",
]

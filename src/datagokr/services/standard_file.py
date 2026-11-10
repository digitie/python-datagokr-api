"""표준데이터의 포털 공개 파일 다운로드 원천. 활용신청·서비스키가 필요 없다.

공공데이터포털 상세 화면의 파일 다운로드와 같은 공개 경로(``download/columList.json`` →
``download/standard.json``)를 쓴다. 이 경로는 표준데이터 **전체**를 돌려주고 인증키를 받지
않는다 — 활용신청하지 않은 키가 Open API에서 403을 받는 dataset도 여기서는 받는다
(2026-11-09 실측: 전통시장 1,393행·지역특화거리 274행).

주차장·박물관미술관·관광지 파일도 같은 경로·같은 검산 규칙을 쓴다(2026-11-10): 선언
건수가 0이거나 포털 다운로드 상한(5만 건)에 닿으면 거부, 페이지 길이가 선언과 다르면 거부,
순회 전후 메타데이터가 바뀌면 거부. 소비자는 전체 순회가 끝난 뒤에만 게시(은퇴 포함)한다.

응답은 JSON이지만 ``Content-Type``이 ``text/html``이고 문자셋을 믿을 수 없다 — UTF-8(BOM
허용)로 읽고 실패하면 CP949로 읽는다. 컬럼명은 Open API의 camelCase가 아니라 원천 테이블의
대문자 snake(``MRKT_NM``)다. 소문자로 바꾸면 typed 모델의 필드명과 같다(``mrkt_nm``) —
원문 행은 ``raw``에 그대로 남긴다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from datagokr.exceptions import ApiErrorResponse
from datagokr.models import StandardItem, StandardPage
from datagokr.transport import AsyncTransport

HEADER_URL = "https://www.data.go.kr/download/columList.json"
DATA_URL = "https://www.data.go.kr/download/standard.json"
FILE_ROW_LIMIT = 50_000
"""포털 다운로드의 건수 상한. 이 값에 닿은 집합은 전체 자료로 게시하지 않는다."""
MAX_FILE_PAGE_SIZE = 10_000

T = TypeVar("T", bound=StandardItem)


@dataclass(frozen=True, slots=True)
class StandardFileSpec:
    """포털 공개 파일 한 종의 식별·검산 규칙."""

    dataset_id: str
    """공공데이터포털 표준데이터 번호(``publicDataPk``)."""
    table_name: str
    """원천 서비스 테이블(``svcTableNm``) — 다른 dataset을 받는 사고를 막는다."""
    required_columns: frozenset[str]
    """``colNmList``에 반드시 있어야 하는 대문자 컬럼."""


TRADITIONAL_MARKET_FILE = StandardFileSpec(
    dataset_id="15012894",
    table_name="tn_pubr_public_trdit_mrkt_svc",
    required_columns=frozenset({"MRKT_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE"}),
)
SPECIAL_STREET_FILE = StandardFileSpec(
    dataset_id="15017322",
    table_name="tn_pubr_public_area_spcliz_stret_svc",
    required_columns=frozenset({"STRET_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE"}),
)
# 2026-11-10 실측 — 주차장 18,994행(2페이지 — 페이지 크기 1만·5천·단일 페이지 결과가 같다)·
# 박물관미술관 1,070행·관광지 897행. 주차장 행에는 ``colNmList``에 없는 ``INSTT_CODE``도 실린다. 운영 키가 Open API에서
# 403(SERVICE_KEY_IS_NOT_REGISTERED_ERROR)을 받아도 공개 파일은 받는다.
PARKING_LOT_FILE = StandardFileSpec(
    dataset_id="15012896",
    table_name="tn_pubr_prkplce_info_svc",
    required_columns=frozenset(
        {"PRKPLCE_NO", "PRKPLCE_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE"}
    ),
)
MUSEUM_ART_GALLERY_FILE = StandardFileSpec(
    dataset_id="15017323",
    table_name="tn_pubr_public_museum_artgr_info_svc",
    required_columns=frozenset({"FCLTY_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE"}),
)
TOURIST_ATTRACTION_FILE = StandardFileSpec(
    dataset_id="15021141",
    table_name="tn_pubr_public_trrsrt_svc",
    required_columns=frozenset({"TRRSRT_NM", "RDNMADR", "LNMADR", "LATITUDE", "LONGITUDE"}),
)


def _error(code: str, spec: StandardFileSpec, detail: str = "") -> ApiErrorResponse:
    message = f"public standard file {spec.dataset_id} validation failed"
    return ApiErrorResponse(code=code, message=f"{message}: {detail}" if detail else message)


def decode_file_json(content: bytes) -> Any:
    """포털 파일 응답을 JSON으로 읽는다 — UTF-8(BOM 허용) 다음 CP949."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp949")
    return json.loads(text)


def _header(content: bytes, spec: StandardFileSpec) -> tuple[int, str, tuple[str, ...]]:
    try:
        value = decode_file_json(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _error("FILE_HEADER_INVALID", spec) from None
    if not isinstance(value, dict):
        raise _error("FILE_HEADER_INVALID", spec)
    total, table = value.get("totalCount"), value.get("tableVO")
    if type(total) is not int or not 0 < total < FILE_ROW_LIMIT or not isinstance(table, dict):
        # 없는 dataset은 HTTP 200 + {"error": "..."}다 — 포털 문구를 그대로 싣는다.
        portal = value.get("error")
        raise _error("FILE_TOTAL_INVALID_OR_LIMITED", spec, str(portal or repr(total)))
    name, columns = table.get("svcTableNm"), table.get("colNmList")
    if (
        table.get("publicDataPk") != spec.dataset_id
        or name != spec.table_name
        or not isinstance(columns, list)
        or not all(isinstance(column, str) for column in columns)
        or len(columns) != len(set(columns))
        or not spec.required_columns.issubset(columns)
    ):
        raise _error("FILE_COLUMNS_INVALID", spec)
    return total, name, tuple(columns)


class StandardFileSource(Generic[T]):
    """표준데이터 포털 공개 파일을 typed 페이지로 순회한다(서비스키를 보내지 않는다)."""

    def __init__(
        self, *, transport: AsyncTransport, spec: StandardFileSpec, model_type: type[T],
    ) -> None:
        self._transport = transport
        self.spec = spec
        self._adapter: TypeAdapter[T] = TypeAdapter(model_type)

    async def iter_pages(
        self, *, num_of_rows: int = MAX_FILE_PAGE_SIZE, max_pages: int | None = None,
    ) -> AsyncIterator[StandardPage[T]]:
        """전체 파일을 페이지로 내준다. 한 행이라도 검증에 실패하면 전체를 거부한다.

        Open API 경로(``list``)는 기형 행을 조용히 건너뛰지만, 파일은 은퇴까지 결정하는
        전체 snapshot이므로 짧은 집합을 성공으로 내지 않는다.
        """
        spec = self.spec
        if not 1 <= num_of_rows <= MAX_FILE_PAGE_SIZE or (max_pages is not None and max_pages <= 0):
            raise ValueError("invalid public standard file page bounds")
        header_params = {"pk": spec.dataset_id, "ext": "JSON"}
        initial = _header(await self._transport.get(HEADER_URL, params=header_params), spec)
        total, table, columns = initial
        page_count = (total + num_of_rows - 1) // num_of_rows
        if max_pages is not None and max_pages < page_count:
            raise _error("FILE_PAGE_LIMIT", spec)
        for page_no in range(1, page_count + 1):
            params: dict[str, Any] = {
                "publicDataPk": spec.dataset_id,
                "totalCount": total,
                "svcTableNm": table,
                "colNmList": list(columns),
                "perPage": num_of_rows,
                "page": page_no,
            }
            try:
                raw = decode_file_json(await self._transport.get(DATA_URL, params=params))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise _error("FILE_PAGE_INVALID", spec, f"page {page_no}") from None
            expected = min(num_of_rows, total - (page_no - 1) * num_of_rows)
            if (
                not isinstance(raw, list)
                or len(raw) != expected
                or not all(isinstance(row, dict) for row in raw)
            ):
                got = len(raw) if isinstance(raw, list) else type(raw).__name__
                raise _error("FILE_PAGE_INCOMPLETE", spec, f"page {page_no}: {got}/{expected}")
            items: list[T] = []
            for index, row in enumerate(raw):
                try:
                    items.append(
                        self._adapter.validate_python(
                            {**{str(key).lower(): value for key, value in row.items()},
                             "raw": dict(row)}
                        )
                    )
                except PydanticValidationError:
                    raise _error(
                        "FILE_ROW_INVALID", spec, f"page {page_no} row {index}"
                    ) from None
            yield StandardPage[T](
                total_count=total, page_no=page_no, num_of_rows=num_of_rows, items=items,
            )
        # 다운로드 중 카탈로그가 교체되면 섞인 snapshot이다 — 호출자의 원자 게시를 막는다.
        if _header(await self._transport.get(HEADER_URL, params=header_params), spec) != initial:
            raise _error("FILE_METADATA_CHANGED", spec)

    async def iter_all(
        self, *, num_of_rows: int = MAX_FILE_PAGE_SIZE, max_pages: int | None = None,
    ) -> AsyncIterator[T]:
        async for page in self.iter_pages(num_of_rows=num_of_rows, max_pages=max_pages):
            for item in page.items:
                yield item


__all__ = [
    "DATA_URL",
    "FILE_ROW_LIMIT",
    "HEADER_URL",
    "MUSEUM_ART_GALLERY_FILE",
    "PARKING_LOT_FILE",
    "SPECIAL_STREET_FILE",
    "TOURIST_ATTRACTION_FILE",
    "TRADITIONAL_MARKET_FILE",
    "StandardFileSource",
    "StandardFileSpec",
    "decode_file_json",
]

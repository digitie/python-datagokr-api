"""전국주차장정보표준데이터의 포털 파일 다운로드 원천. 인증키를 사용하지 않는다."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from datagokr.exceptions import ApiErrorResponse
from datagokr.models import PublicParkingLot, StandardPage
from datagokr.transport import AsyncTransport

HEADER_URL = "https://www.data.go.kr/download/columList.json"
DATA_URL = "https://www.data.go.kr/download/standard.json"
DATASET_ID = "15012896"
# 포털 다운로드의 5만 건 상한에 걸린 집합을 전체 자료로 게시하지 않는다.
FILE_ROW_LIMIT = 50_000


def _error(code: str) -> ApiErrorResponse:
    return ApiErrorResponse(code=code, message="public parking file validation failed")


def _header(content: bytes) -> tuple[int, str, list[str]]:
    value = json.loads(content)
    if not isinstance(value, dict):
        raise _error("FILE_HEADER_INVALID")
    total, table = value.get("totalCount"), value.get("tableVO")
    if type(total) is not int or not 0 < total < FILE_ROW_LIMIT or not isinstance(table, dict):
        raise _error("FILE_TOTAL_INVALID_OR_LIMITED")
    name, columns = table.get("svcTableNm"), table.get("colNmList")
    required = {"PRKPLCE_NO", "PRKPLCE_NM", "RDNMADR", "LNMADR", "REFERENCE_DATE"}
    if (table.get("publicDataPk") != DATASET_ID or name != "tn_pubr_prkplce_info_svc"
            or not isinstance(columns, list) or not all(isinstance(x, str) for x in columns)
            or len(columns) != len(set(columns)) or not required.issubset(columns)):
        raise _error("FILE_COLUMNS_INVALID")
    return total, name, columns


async def iter_parking_file_pages(
    transport: AsyncTransport, *, num_of_rows: int = 10_000, max_pages: int | None = None,
) -> AsyncIterator[StandardPage[PublicParkingLot]]:
    if not 1 <= num_of_rows <= 10_000 or (max_pages is not None and max_pages <= 0):
        raise ValueError("invalid public parking file page bounds")
    header_params = {"pk": DATASET_ID, "ext": "JSON"}
    initial = _header(await transport.get(HEADER_URL, params=header_params))
    total, table, columns = initial
    page_count = (total + num_of_rows - 1) // num_of_rows
    if max_pages is not None and max_pages < page_count:
        raise _error("FILE_PAGE_LIMIT")
    for page_no in range(1, page_count + 1):
        params: dict[str, Any] = {
            "publicDataPk": DATASET_ID, "totalCount": total, "svcTableNm": table,
            "colNmList": columns, "perPage": num_of_rows, "page": page_no,
        }
        raw = json.loads(await transport.get(DATA_URL, params=params))
        expected = min(num_of_rows, total - (page_no - 1) * num_of_rows)
        if (not isinstance(raw, list) or len(raw) != expected
                or not all(isinstance(x, dict) for x in raw)):
            raise _error("FILE_PAGE_INCOMPLETE")
        # 공식 파일의 대문자 컬럼을 기존 typed 필드에 대응한다. 원문은 그대로 보존한다.
        items = [PublicParkingLot.model_validate({
            **{key.lower(): value for key, value in row.items()}, "raw": dict(row),
        }) for row in raw]
        yield StandardPage[PublicParkingLot](
            total_count=total, page_no=page_no, num_of_rows=num_of_rows, items=items,
        )
    # 다운로드 중 카탈로그 교체가 관측되면 호출자의 원자 게시를 중단시킨다.
    if _header(await transport.get(HEADER_URL, params=header_params)) != initial:
        raise _error("FILE_METADATA_CHANGED")

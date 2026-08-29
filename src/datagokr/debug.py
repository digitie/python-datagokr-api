"""디버그 UI와 fixture 저장에 재사용하는 공통 헬퍼.

`examples/streamlit_debug_ui.py`는 이 모듈의 `jsonable`/`redact_sensitive`/
`debug_error`/`save_fixture`와 `DataGoKrClient.debug_fetch()`가 반환하는
`DebugRun`만으로 동작한다. Streamlit 파일 안에 이 로직을 인라인으로 다시
구현하지 않는다 — 재사용/단위테스트가 가능해야 하기 때문이다.
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from datagokr.exceptions import (
    ApiErrorResponse,
    ConfigError,
    TransportError,
    UnknownDatasetError,
)
from datagokr.exceptions import ValidationError as DataGoKrValidationError

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "x-api-key",
        "api_key",
        "apikey",
        "servicekey",
        "service_key",
        "service-key",
        "access_token",
        "refresh_token",
    }
)

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(key) for key in SENSITIVE_KEYS) + r")=[^&\s\"']+"
)

DEFAULT_ASSERTION: Mapping[str, Any] = {
    "mode": "snapshot",
    "exclude_fields": ["fetched_at", "request_id", "updated_at"],
    "required_fields": [],
}


@dataclass(frozen=True, slots=True)
class DebugRun:
    """API 호출 한 번의 입력, 요청, 응답, 파싱/가공 결과 묶음입니다."""

    function: str
    input: Mapping[str, Any]
    request: Mapping[str, Any]
    response: Mapping[str, Any]
    parsed: Any
    processed: Any
    trace: tuple[str, ...]
    error: dict[str, Any] | None = None
    catalog: Any | None = None


def jsonable(obj: Any) -> Any:
    """Pydantic 모델, dataclass, enum, 날짜 값을 JSON 호환 값으로 바꿉니다."""

    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if is_dataclass(obj) and not isinstance(obj, type):
        return jsonable(asdict(obj))
    if isinstance(obj, Mapping):
        return {str(key): jsonable(value) for key, value in obj.items()}
    if isinstance(obj, list | tuple | set | frozenset):
        return [jsonable(value) for value in obj]
    if isinstance(obj, datetime | date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    return obj


def redact_sensitive(obj: Any) -> Any:
    """dict/list/문자열에서 서비스키·토큰 성격의 값을 마스킹합니다."""

    if isinstance(obj, Mapping):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            key_text = str(key)
            if key_text.lower() in SENSITIVE_KEYS:
                result[key_text] = "<REDACTED>"
            else:
                result[key_text] = redact_sensitive(value)
        return result
    if isinstance(obj, list | tuple):
        return [redact_sensitive(value) for value in obj]
    if isinstance(obj, str):
        return _SENSITIVE_VALUE_PATTERN.sub(r"\1=<REDACTED>", obj)
    return obj


def debug_error(exc: BaseException) -> dict[str, Any]:
    """예외를 디버그 UI/fixture에 넣기 쉬운 구조화 dict로 변환합니다.

    `{type, message, traceback}`은 항상 채우고, 패키지 자체 예외 타입이면
    provider별 필드(`status_code`/`result_code`/`failure_kind`/`retryable`)를
    덧붙입니다. 반환값은 항상 `redact_sensitive()`를 통과합니다.
    """

    payload: dict[str, Any] = {
        "type": exc.__class__.__name__,
        "module": exc.__class__.__module__,
        "message": str(exc),
        "traceback": traceback.format_exception(exc),
    }
    if isinstance(exc, ApiErrorResponse):
        payload.update(
            {
                "result_code": exc.code,
                "failure_kind": "api_error",
                "retryable": False,
            }
        )
    elif isinstance(exc, TransportError):
        status_code = exc.status_code
        is_server_side = status_code is not None and status_code >= 500
        payload.update(
            {
                "status_code": status_code,
                "failure_kind": "server" if is_server_side else "transport",
                "retryable": status_code is None or is_server_side or status_code == 429,
            }
        )
    elif isinstance(exc, UnknownDatasetError):
        payload.update({"failure_kind": "unknown_dataset", "retryable": False})
    elif isinstance(exc, ConfigError | DataGoKrValidationError):
        payload.update({"failure_kind": "invalid_request", "retryable": False})
    elif isinstance(exc, PydanticValidationError):
        payload.update(
            {
                "failure_kind": "parse",
                "retryable": False,
                "validation_errors": exc.errors(include_url=False),
            }
        )
    return cast(dict[str, Any], redact_sensitive(payload))


def save_fixture(
    *,
    base_dir: str | PathLike[str],
    function_name: str,
    case_name: str,
    description: str,
    input_data: Any,
    request_data: Any,
    response_data: Any,
    parsed_result: Any,
    processed_result: Any,
    assertion: Mapping[str, Any] | None = None,
    library_version: str | None = None,
    overwrite: bool = False,
) -> Path:
    """디버그 실행 결과를 pytest replay용 fixture JSON 파일로 저장합니다."""

    safe_case_name = slugify_case_name(case_name)
    fixture_dir = Path(base_dir) / function_name
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / f"{safe_case_name}.json"
    if fixture_path.exists() and not overwrite:
        raise FileExistsError(f"Fixture already exists: {fixture_path}")

    fixture = {
        "name": safe_case_name,
        "function": function_name,
        "description": description,
        "input": redact_sensitive(jsonable(input_data)),
        "request": redact_sensitive(jsonable(request_data)),
        "response": redact_sensitive(jsonable(response_data)),
        "parsed": jsonable(parsed_result),
        "processed": jsonable(processed_result),
        "assertion": dict(assertion or DEFAULT_ASSERTION),
        "meta": {
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "library_version": library_version,
            "source": "debug_ui",
        },
    }
    with fixture_path.open("w", encoding="utf-8") as handle:
        json.dump(fixture, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return fixture_path


def slugify_case_name(value: str) -> str:
    """fixture 파일명에 쓸 수 있도록 case 이름을 느슨하게 정규화합니다."""

    cleaned = value.strip().lower()
    slug = re.sub(r"[^\w.-]+", "-", cleaned, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-._")
    return slug or "case"

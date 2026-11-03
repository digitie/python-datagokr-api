from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DataGoKrError(Exception):
    """Base exception for python-datagokr-api."""


class ConfigError(DataGoKrError, ValueError):
    """Raised when runtime configuration is invalid."""


class ValidationError(DataGoKrError, ValueError):
    """Raised when a caller-supplied request parameter is invalid."""


class UnknownDatasetError(DataGoKrError, KeyError):
    """Raised when a dataset slug is not recognized."""


class TransportError(DataGoKrError):
    """Raised when HTTP transport fails before an API response is parsed."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ResponseParseError(DataGoKrError):
    """정상 성공 여부나 항목 구조를 확인할 수 없는 제공기관 응답."""


@dataclass
class ApiErrorResponse(DataGoKrError):
    """Raised when data.go.kr returns an explicit non-normal result code."""

    code: str
    message: str
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __reduce__(self) -> tuple[type[ApiErrorResponse], tuple[str, str, dict[str, Any] | None]]:
        return (self.__class__, (self.code, self.message, self.payload))


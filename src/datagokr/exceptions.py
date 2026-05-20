from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DataGoKrError(Exception):
    """Base exception for python-datagokr-api."""


class ConfigError(DataGoKrError, ValueError):
    """Raised when runtime configuration is invalid."""


class TransportError(DataGoKrError):
    """Raised when HTTP transport fails before an API response is parsed."""


@dataclass(slots=True)
class ApiErrorResponse(DataGoKrError):
    """Raised when data.go.kr returns an explicit non-normal result code."""

    code: str
    message: str
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


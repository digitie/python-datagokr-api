from __future__ import annotations

import os
from dataclasses import dataclass

from datagokr.exceptions import ConfigError

DEFAULT_DATA_GO_KR_BASE_URL = "https://api.data.go.kr/openapi"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_PAGE_SIZE = 1000

API_KEY_ENV_NAMES = (
    "DATA_GO_KR_SERVICE_KEY",
)


@dataclass(frozen=True, slots=True)
class DataGoKrConfig:
    """Runtime configuration loaded from explicit args and environment variables."""

    api_key: str | None
    base_url: str = DEFAULT_DATA_GO_KR_BASE_URL
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | str | None = None,
    ) -> DataGoKrConfig:
        resolved_api_key = api_key
        if resolved_api_key is None:
            for env_name in API_KEY_ENV_NAMES:
                value = os.getenv(env_name)
                if value:
                    resolved_api_key = value
                    break
        resolved_base_url = (
            base_url or os.getenv("DATAGOKR_BASE_URL") or DEFAULT_DATA_GO_KR_BASE_URL
        )
        return cls(
            api_key=(resolved_api_key or None),
            base_url=resolved_base_url.rstrip("/"),
            timeout=_resolve_timeout(
                timeout if timeout is not None else os.getenv("DATAGOKR_TIMEOUT")
            ),
        )


def _resolve_timeout(value: float | str | None) -> float:
    if value is None or value == "":
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError("DATAGOKR_TIMEOUT must be a positive number") from exc
    if timeout <= 0:
        raise ConfigError("DATAGOKR_TIMEOUT must be greater than 0")
    return timeout

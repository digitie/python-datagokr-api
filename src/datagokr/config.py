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
    rustfs_endpoint_url: str | None = None
    rustfs_access_key_id: str | None = None
    rustfs_secret_access_key: str | None = None
    rustfs_bucket: str = "datagokr-uploads"
    rustfs_region_name: str = "us-east-1"

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | str | None = None,
        rustfs_endpoint_url: str | None = None,
        rustfs_access_key_id: str | None = None,
        rustfs_secret_access_key: str | None = None,
        rustfs_bucket: str | None = None,
        rustfs_region_name: str | None = None,
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

        resolved_rustfs_endpoint = (
            rustfs_endpoint_url
            or os.getenv("DATAGOKR_RUSTFS_ENDPOINT_URL")
            or os.getenv("RUSTFS_ENDPOINT_URL")
        )
        resolved_rustfs_access_key = (
            rustfs_access_key_id
            or os.getenv("DATAGOKR_RUSTFS_ACCESS_KEY_ID")
            or os.getenv("RUSTFS_ACCESS_KEY_ID")
        )
        resolved_rustfs_secret_key = (
            rustfs_secret_access_key
            or os.getenv("DATAGOKR_RUSTFS_SECRET_ACCESS_KEY")
            or os.getenv("RUSTFS_SECRET_ACCESS_KEY")
        )
        resolved_rustfs_bucket = (
            rustfs_bucket
            or os.getenv("DATAGOKR_RUSTFS_BUCKET")
            or os.getenv("RUSTFS_BUCKET")
            or "datagokr-uploads"
        )
        resolved_rustfs_region = (
            rustfs_region_name
            or os.getenv("DATAGOKR_RUSTFS_REGION_NAME")
            or os.getenv("RUSTFS_REGION_NAME")
            or "us-east-1"
        )

        return cls(
            api_key=(resolved_api_key or None),
            base_url=resolved_base_url.rstrip("/"),
            timeout=_resolve_timeout(
                timeout if timeout is not None else os.getenv("DATAGOKR_TIMEOUT")
            ),
            rustfs_endpoint_url=resolved_rustfs_endpoint or None,
            rustfs_access_key_id=resolved_rustfs_access_key or None,
            rustfs_secret_access_key=resolved_rustfs_secret_key or None,
            rustfs_bucket=resolved_rustfs_bucket,
            rustfs_region_name=resolved_rustfs_region,
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


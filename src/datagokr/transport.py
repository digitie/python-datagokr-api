from __future__ import annotations

import time
from typing import Any, Protocol

import httpx

from datagokr.config import DataGoKrConfig
from datagokr.exceptions import TransportError


class SyncTransport(Protocol):
    def get(self, path: str, params: dict[str, Any] | None = None) -> bytes: ...

    def close(self) -> None: ...


class SyncHttpxTransport:
    """httpx-backed synchronous transport for data.go.kr standard APIs."""

    def __init__(self, config: DataGoKrConfig) -> None:
        self._client = httpx.Client(timeout=config.timeout, follow_redirects=True)
        self._api_key = config.api_key
        self._base_url = config.base_url.rstrip("/")

    def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        url = _absolute_url(path, self._base_url)
        request_params = dict(params or {})
        if self._api_key and "serviceKey" not in request_params:
            request_params["serviceKey"] = self._api_key
        last_error: httpx.TransportError | None = None
        for attempt in range(3):
            try:
                response = self._client.get(url, params=request_params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TransportError(str(exc)) from exc
            except httpx.TransportError as exc:
                last_error = exc
                if attempt == 2:
                    break
                time.sleep(0.5 * (attempt + 1))
            else:
                return response.content
        message = str(last_error) if last_error is not None else "unknown transport error"
        raise TransportError(message)

    def close(self) -> None:
        self._client.close()


def _absolute_url(path: str, base_url: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{base_url}/{path.lstrip('/')}"

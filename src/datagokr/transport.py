from __future__ import annotations

import asyncio
import random
from typing import Any, Protocol

import httpx

from datagokr._httpx import send_after_token
from datagokr._ratelimit import AsyncTokenBucket
from datagokr.config import DataGoKrConfig
from datagokr.exceptions import TransportError


class AsyncTransport(Protocol):
    async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes: ...

    async def aclose(self) -> None: ...


class AsyncHttpxTransport:
    """재시도와 redirect를 같은 TPS 예산으로 전송하는 비동기 HTTP 계층."""

    def __init__(
        self, config: DataGoKrConfig, *, rate_limiter: AsyncTokenBucket | None = None,
    ) -> None:
        self.rate_limiter = (
            rate_limiter if rate_limiter is not None else AsyncTokenBucket(config.max_rps)
        )
        self._client: httpx.AsyncClient | None = None
        self._timeout = config.timeout
        self._api_key = config.api_key
        self._base_url = config.base_url.rstrip("/")
        self._closed = False

    async def get(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        if self._closed:
            raise RuntimeError("transport is closed")
        url = _absolute_url(path, self._base_url)
        request_params = dict(params or {})
        if self._api_key and "serviceKey" not in request_params:
            request_params["serviceKey"] = self._api_key
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=True)
        for attempt in range(3):
            try:
                request = self._client.build_request("GET", url, params=request_params)
                await self.rate_limiter.acquire()
                response = await send_after_token(self._client, request, self.rate_limiter)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                safe_url = exc.request.url.copy_remove_param("serviceKey")
                raise TransportError(
                    f"HTTP {exc.response.status_code} error for url '{safe_url}'",
                    status_code=exc.response.status_code,
                ) from None
            except httpx.TransportError:
                if attempt == 2:
                    raise TransportError("HTTP transport failed after 3 attempts") from None
                await asyncio.sleep(0.5 * (attempt + 1) * random.uniform(0.5, 1.5))
            else:
                return response.content
        raise AssertionError("unreachable")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._closed = True


def _absolute_url(path: str, base_url: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{base_url}/{path.lstrip('/')}"

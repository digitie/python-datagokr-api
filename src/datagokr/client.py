from __future__ import annotations

import weakref
from collections.abc import Mapping
from types import TracebackType
from typing import Any

from datagokr.catalog import get_api_catalog_entry
from datagokr.config import DataGoKrConfig
from datagokr.debug import DebugRun, debug_error, jsonable, redact_sensitive
from datagokr.services import (
    AgriWeatherService,
    CulturalFestivalService,
    KwaterSluiceService,
    MuseumArtGalleryService,
    ParkingLotService,
    SpecialStreetService,
    TouristAttractionService,
)
from datagokr.services.file_data import FileDataService
from datagokr.transport import SyncHttpxTransport


class DataGoKrClient:
    """Synchronous facade for selected data.go.kr standard open APIs.

    Holds a pooled ``httpx.Client``; use as a context manager or call
    ``close()`` explicitly to release its connections/file descriptors.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.config = DataGoKrConfig.from_env(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._transport = SyncHttpxTransport(self.config)
        try:
            self.museum_art = MuseumArtGalleryService(transport=self._transport)
            self.parking = ParkingLotService(transport=self._transport)
            self.tourist_attraction = TouristAttractionService(transport=self._transport)
            self.festival = CulturalFestivalService(transport=self._transport)
            self.special_street = SpecialStreetService(transport=self._transport)
            self.file_data = FileDataService(transport=self._transport)
            self.agri_weather = AgriWeatherService(transport=self._transport)
            self.kwater_sluice = KwaterSluiceService(transport=self._transport)
        except Exception:
            self._transport.close()
            raise
        self.closed = False
        weakref.finalize(self, self._transport.close)

    def save_to_local(self, file_path: str, content: bytes) -> None:
        """Save content to the local filesystem."""
        from datagokr.storage import save_to_local as _save_local

        _save_local(file_path, content)

    def save_to_rustfs(
        self,
        file_path: str,
        content: bytes,
        *,
        bucket: str | None = None,
        object_key: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        """Save content to both local filesystem and RustFS object storage.

        Falls back to client config values for unspecified S3 options.
        """
        from datagokr.storage import save_to_rustfs as _save_rustfs

        _save_rustfs(
            file_path,
            content,
            bucket=(bucket or self.config.rustfs_bucket),
            object_key=object_key,
            region_name=(region_name or self.config.rustfs_region_name),
            endpoint_url=(endpoint_url or self.config.rustfs_endpoint_url),
            access_key_id=(access_key_id or self.config.rustfs_access_key_id),
            secret_access_key=(secret_access_key or self.config.rustfs_secret_access_key),
        )

    def debug_fetch(
        self,
        service_key: str,
        *,
        params: Mapping[str, Any] | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_type: str = "json",
    ) -> DebugRun:
        """카탈로그 메타데이터로 라우팅해 임의 API를 실행하고 디버그 정보를 반환합니다.

        `service_key`는 `datagokr.catalog.get_api_catalog()`가 반환하는 항목의
        `key`입니다. 이 메서드는 어떤 API를 호출할지 카탈로그의
        `service_attr`/`list_method`/`bound_args`로만 결정하며, 함수명별
        `if/elif` 분기는 두지 않는다 — 새 API는 카탈로그에 항목을 추가하는 것만으로
        여기서 실행 가능해야 한다.
        """

        entry = get_api_catalog_entry(service_key)
        input_data = redact_sensitive(
            {
                "service_key": entry.key,
                "params": dict(params or {}),
                "page_no": page_no,
                "num_of_rows": num_of_rows,
                "response_type": response_type,
            }
        )
        trace: list[str] = [
            f"카탈로그 조회: {entry.key} ({entry.title})",
            f"data_source: {entry.data_source}",
            f"endpoint: {entry.endpoint}",
        ]

        service = _resolve_attr_path(self, entry.service_attr)
        method = getattr(service, entry.list_method)

        call_kwargs: dict[str, Any] = dict(entry.bound_args)
        call_kwargs["page_no"] = page_no
        call_kwargs[entry.num_rows_kwarg] = num_of_rows
        if entry.supports_response_type:
            call_kwargs["response_type"] = response_type
        for key, value in (params or {}).items():
            if value not in (None, ""):
                call_kwargs[key] = value

        request = {
            "method": "GET",
            "endpoint": entry.endpoint,
            "call": f"{entry.service_attr}.{entry.list_method}",
            "kwargs": redact_sensitive(jsonable(call_kwargs)),
        }
        trace.append(f"호출: {entry.service_attr}.{entry.list_method}(**kwargs)")

        try:
            page = method(**call_kwargs)
        except Exception as exc:
            trace.append(f"실행 실패: {exc.__class__.__name__}")
            return DebugRun(
                function=entry.key,
                input=input_data,
                request=request,
                response={},
                parsed=None,
                processed=None,
                trace=tuple(trace),
                error=debug_error(exc),
                catalog=entry,
            )

        trace.append(f"응답 item {len(page)}건 파싱 완료")
        response = {"status_code": 200, "body": jsonable(page)}
        return DebugRun(
            function=entry.key,
            input=input_data,
            request=request,
            response=response,
            parsed=page,
            processed=list(page.items),
            trace=tuple(trace),
            catalog=entry,
        )

    def __enter__(self) -> DataGoKrClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._transport.close()
        self.closed = True


def _resolve_attr_path(root: object, dotted_path: str) -> Any:
    """`"kwater_sluice.hourly"` 같은 점(.) 구분 속성 경로를 따라가 값을 찾습니다."""

    value: Any = root
    for part in dotted_path.split("."):
        value = getattr(value, part)
    return value


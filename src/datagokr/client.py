from __future__ import annotations

import weakref
from types import TracebackType

from datagokr.config import DataGoKrConfig
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


from __future__ import annotations

from types import TracebackType

from datagokr.config import DataGoKrConfig
from datagokr.services import (
    CulturalFestivalService,
    MuseumArtGalleryService,
    ParkingLotService,
    TouristAttractionService,
)
from datagokr.transport import SyncHttpxTransport


class DataGoKrClient:
    """Synchronous facade for selected data.go.kr standard open APIs."""

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
        self.museum_art = MuseumArtGalleryService(transport=self._transport)
        self.parking = ParkingLotService(transport=self._transport)
        self.tourist_attraction = TouristAttractionService(transport=self._transport)
        self.festival = CulturalFestivalService(transport=self._transport)
        self.closed = False

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


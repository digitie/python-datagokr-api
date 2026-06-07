from __future__ import annotations

from datagokr.client import DataGoKrClient
from datagokr.config import DataGoKrConfig
from datagokr.models import (
    AgriWeatherObservationStation,
    KwaterSluiceRecord,
    OpenApiPage,
    PublicCulturalFestival,
    PublicMuseumArtGallery,
    PublicParkingLot,
    PublicTouristAttraction,
    StandardPage,
)
from datagokr.services import (
    AGRI_WEATHER_STATION_ENDPOINT,
    CULTURAL_FESTIVAL_ENDPOINT,
    KWATER_SLUICE_DAY_ENDPOINT,
    KWATER_SLUICE_HOUR_ENDPOINT,
    KWATER_SLUICE_TEN_MINUTE_ENDPOINT,
    MUSEUM_ART_GALLERY_ENDPOINT,
    PARKING_LOT_ENDPOINT,
    TOURIST_ATTRACTION_ENDPOINT,
    AgriWeatherService,
    CulturalFestivalService,
    KwaterSluiceService,
    MuseumArtGalleryService,
    ParkingLotService,
    TouristAttractionService,
)
from datagokr.storage import save_to_local, save_to_rustfs

__version__ = "0.1.0"
PROVIDER_NAME = "python-datagokr-api"

__all__ = [
    "AGRI_WEATHER_STATION_ENDPOINT",
    "CULTURAL_FESTIVAL_ENDPOINT",
    "KWATER_SLUICE_DAY_ENDPOINT",
    "KWATER_SLUICE_HOUR_ENDPOINT",
    "KWATER_SLUICE_TEN_MINUTE_ENDPOINT",
    "MUSEUM_ART_GALLERY_ENDPOINT",
    "PARKING_LOT_ENDPOINT",
    "PROVIDER_NAME",
    "TOURIST_ATTRACTION_ENDPOINT",
    "AgriWeatherObservationStation",
    "AgriWeatherService",
    "CulturalFestivalService",
    "DataGoKrClient",
    "DataGoKrConfig",
    "KwaterSluiceRecord",
    "KwaterSluiceService",
    "MuseumArtGalleryService",
    "OpenApiPage",
    "ParkingLotService",
    "PublicCulturalFestival",
    "PublicMuseumArtGallery",
    "PublicParkingLot",
    "PublicTouristAttraction",
    "StandardPage",
    "TouristAttractionService",
    "__version__",
    "save_to_local",
    "save_to_rustfs",
]


from __future__ import annotations

from datagokr.services.openapi import (
    AGRI_WEATHER_STATION_ENDPOINT,
    KWATER_SLUICE_DAY_ENDPOINT,
    KWATER_SLUICE_HOUR_ENDPOINT,
    KWATER_SLUICE_TEN_MINUTE_ENDPOINT,
    AgriWeatherService,
    DataGoKrOpenApiService,
    KwaterSluiceService,
)
from datagokr.services.standard import (
    CULTURAL_FESTIVAL_ENDPOINT,
    MUSEUM_ART_GALLERY_ENDPOINT,
    PARKING_LOT_ENDPOINT,
    TOURIST_ATTRACTION_ENDPOINT,
    CulturalFestivalService,
    MuseumArtGalleryService,
    ParkingLotService,
    StandardOpenApiService,
    TouristAttractionService,
)

__all__ = [
    "AGRI_WEATHER_STATION_ENDPOINT",
    "CULTURAL_FESTIVAL_ENDPOINT",
    "KWATER_SLUICE_DAY_ENDPOINT",
    "KWATER_SLUICE_HOUR_ENDPOINT",
    "KWATER_SLUICE_TEN_MINUTE_ENDPOINT",
    "MUSEUM_ART_GALLERY_ENDPOINT",
    "PARKING_LOT_ENDPOINT",
    "TOURIST_ATTRACTION_ENDPOINT",
    "AgriWeatherService",
    "CulturalFestivalService",
    "DataGoKrOpenApiService",
    "KwaterSluiceService",
    "MuseumArtGalleryService",
    "ParkingLotService",
    "StandardOpenApiService",
    "TouristAttractionService",
]

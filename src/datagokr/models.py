from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DataGoKrModel(BaseModel):
    """Base Pydantic model for public data.go.kr payloads."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def _blank_string_to_none(cls, value: Any) -> Any:
        if value == "":
            return None
        return value


T = TypeVar("T")


class StandardPage(DataGoKrModel, Generic[T]):
    """Uniform container for standard open API list responses."""

    total_count: int = 0
    page_no: int = 1
    num_of_rows: int = 100
    items: list[T] = Field(default_factory=list)

    @property
    def total_pages(self) -> int:
        if self.num_of_rows <= 0:
            return 0
        return (self.total_count + self.num_of_rows - 1) // self.num_of_rows

    def __iter__(self) -> Iterator[T]:  # type: ignore[override]
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


class StandardItem(DataGoKrModel):
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw", mode="before")
    @classmethod
    def _default_raw(cls, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}


class PublicMuseumArtGallery(StandardItem):
    fclty_nm: str | None = Field(default=None, alias="fcltyNm")
    fclty_type: str | None = Field(default=None, alias="fcltyType")
    rdnmadr: str | None = None
    lnmadr: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    oper_phone_number: str | None = Field(default=None, alias="operPhoneNumber")
    oper_institution_nm: str | None = Field(default=None, alias="operInstitutionNm")
    homepage_url: str | None = Field(default=None, alias="homepageUrl")
    fclty_info: str | None = Field(default=None, alias="fcltyInfo")
    weekday_oper_open_hhmm: str | None = Field(default=None, alias="weekdayOperOpenHhmm")
    weekday_oper_colse_hhmm: str | None = Field(default=None, alias="weekdayOperColseHhmm")
    holiday_oper_open_hhmm: str | None = Field(default=None, alias="holidayOperOpenHhmm")
    holiday_close_open_hhmm: str | None = Field(default=None, alias="holidayCloseOpenHhmm")
    rstde_info: str | None = Field(default=None, alias="rstdeInfo")
    adult_chrge: int | None = Field(default=None, alias="adultChrge")
    yngbgs_chrge: int | None = Field(default=None, alias="yngbgsChrge")
    child_chrge: int | None = Field(default=None, alias="childChrge")
    etc_chrge_info: str | None = Field(default=None, alias="etcChrgeInfo")
    fclty_intrcn: str | None = Field(default=None, alias="fcltyIntrcn")
    trnsport_info: str | None = Field(default=None, alias="trnsportInfo")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    institution_nm: str | None = Field(default=None, alias="institutionNm")
    reference_date: date | None = Field(default=None, alias="referenceDate")
    instt_code: str | None = None
    instt_nm: str | None = None


class PublicParkingLot(StandardItem):
    prkplce_no: str | None = Field(default=None, alias="prkplceNo")
    prkplce_nm: str | None = Field(default=None, alias="prkplceNm")
    prkplce_se: str | None = Field(default=None, alias="prkplceSe")
    prkplce_type: str | None = Field(default=None, alias="prkplceType")
    rdnmadr: str | None = None
    lnmadr: str | None = None
    prkcmprt: int | None = None
    feeding_se: str | None = Field(default=None, alias="feedingSe")
    enforce_se: str | None = Field(default=None, alias="enforceSe")
    oper_day: str | None = Field(default=None, alias="operDay")
    weekday_oper_open_hhmm: str | None = Field(default=None, alias="weekdayOperOpenHhmm")
    weekday_oper_colse_hhmm: str | None = Field(default=None, alias="weekdayOperColseHhmm")
    sat_oper_oper_open_hhmm: str | None = Field(default=None, alias="satOperOperOpenHhmm")
    sat_oper_close_hhmm: str | None = Field(default=None, alias="satOperCloseHhmm")
    holiday_oper_open_hhmm: str | None = Field(default=None, alias="holidayOperOpenHhmm")
    holiday_close_open_hhmm: str | None = Field(default=None, alias="holidayCloseOpenHhmm")
    parkingchrge_info: str | None = Field(default=None, alias="parkingchrgeInfo")
    basic_time: int | None = Field(default=None, alias="basicTime")
    basic_charge: int | None = Field(default=None, alias="basicCharge")
    add_unit_time: int | None = Field(default=None, alias="addUnitTime")
    add_unit_charge: int | None = Field(default=None, alias="addUnitCharge")
    day_cmmtkt_adj_time: float | None = Field(default=None, alias="dayCmmtktAdjTime")
    day_cmmtkt: int | None = Field(default=None, alias="dayCmmtkt")
    month_cmmtkt: int | None = Field(default=None, alias="monthCmmtkt")
    metpay: str | None = None
    spcmnt: str | None = None
    institution_nm: str | None = Field(default=None, alias="institutionNm")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    latitude: float | None = None
    longitude: float | None = None
    pwdbs_ppk_zone_yn: str | None = Field(default=None, alias="pwdbsPpkZoneYn")
    reference_date: date | None = Field(default=None, alias="referenceDate")
    instt_code: str | None = None
    instt_nm: str | None = None


class PublicTouristAttraction(StandardItem):
    trrsrt_nm: str | None = Field(default=None, alias="trrsrtNm")
    trrsrt_se: str | None = Field(default=None, alias="trrsrtSe")
    rdnmadr: str | None = None
    lnmadr: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    ar: float | None = None
    cnvnnc_fclty: str | None = Field(default=None, alias="cnvnncFclty")
    stayng_info: str | None = Field(default=None, alias="stayngInfo")
    mvm_amsmt_fclty: str | None = Field(default=None, alias="mvmAmsmtFclty")
    recrt_cltur_fclty: str | None = Field(default=None, alias="recrtClturFclty")
    hospitality_fclty: str | None = Field(default=None, alias="hospitalityFclty")
    sport_fclty: str | None = Field(default=None, alias="sportFclty")
    appn_date: date | None = Field(default=None, alias="appnDate")
    aceptnc_co: int | None = Field(default=None, alias="aceptncCo")
    prkplce_co: int | None = Field(default=None, alias="prkplceCo")
    trrsrt_intrcn: str | None = Field(default=None, alias="trrsrtIntrcn")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    institution_nm: str | None = Field(default=None, alias="institutionNm")
    reference_date: date | None = Field(default=None, alias="referenceDate")
    instt_code: str | None = None


class PublicCulturalFestival(StandardItem):
    fstvl_nm: str | None = Field(default=None, alias="fstvlNm")
    opar: str | None = None
    fstvl_start_date: date | None = Field(default=None, alias="fstvlStartDate")
    fstvl_end_date: date | None = Field(default=None, alias="fstvlEndDate")
    fstvl_co: str | None = Field(default=None, alias="fstvlCo")
    mnnst_nm: str | None = Field(default=None, alias="mnnstNm")
    auspc_instt_nm: str | None = Field(default=None, alias="auspcInsttNm")
    suprt_instt_nm: str | None = Field(default=None, alias="suprtInsttNm")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    homepage_url: str | None = Field(default=None, alias="homepageUrl")
    relate_info: str | None = Field(default=None, alias="relateInfo")
    rdnmadr: str | None = None
    lnmadr: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    reference_date: date | None = Field(default=None, alias="referenceDate")
    instt_code: str | None = None
    instt_nm: str | None = None

"""API 응답 형태. 화면 JavaScript가 읽는 필드 이름을 여기서 고정한다."""

from pydantic import BaseModel, Field


class OecdCountry(BaseModel):
    country: str
    iso3: str
    rate: float = Field(ge=0)
    rank: int = Field(ge=1)


class OecdYear(BaseModel):
    year: int
    country_count: int = Field(ge=0)
    countries: list[OecdCountry]


class OecdRankings(BaseModel):
    years: list[OecdYear]


class AccidentTrendYear(BaseModel):
    year: int
    nationwide_accidents: int = Field(ge=0)
    nationwide_deaths: int = Field(ge=0)
    seoul_accidents: int = Field(ge=0)
    seoul_injuries: int = Field(ge=0)
    seoul_deaths: int = Field(ge=0)


class AccidentTrend(BaseModel):
    years: list[AccidentTrendYear]


class NationalDeathYear(BaseModel):
    """전국 교통사고 사망자. 65세 이상 값은 OECD 자료가 있는 연도에만 채운다."""

    year: int
    total_deaths: int = Field(ge=0)
    elderly_deaths: int | None = Field(default=None, ge=0)
    elderly_share_percent: float | None = Field(default=None, ge=0, le=100)


class NationalDeaths(BaseModel):
    years: list[NationalDeathYear]


class ChildPedestrian(BaseModel):
    """서울 어린이(12세 이하) 보행자 교통사고."""

    year: int
    accidents: int = Field(ge=0)
    deaths: int = Field(ge=0)


class ElderlyPedestrian(BaseModel):
    """서울 고령(65세 이상) 보행자 교통사고 자치구 합계와 사고율."""

    year: int
    region: str
    districts: int
    accidents: int = Field(ge=0)
    deaths: int = Field(ge=0)
    injuries: int = Field(ge=0)
    population_65plus: int = Field(gt=0)
    accidents_per_10k: float = Field(ge=0)  # 고령인구 1만 명당 고령 보행자 사고(건)
    all_pedestrian_deaths: int = Field(ge=0)
    death_share_percent: float = Field(ge=0, le=100)  # 전체 보행 사망자 중 고령층(%)
    previous_year: int
    accidents_change: int  # 전년 대비 사고 증감(건)
    deaths_change: int  # 전년 대비 사망 증감(명)


class DistrictRate(BaseModel):
    """자치구 한 곳의 고령 보행자 사고율과 전년 대비 변화."""

    district: str
    population_65plus: int = Field(gt=0)
    accidents: int = Field(ge=0)
    hotspots: int = Field(ge=0)  # 사고다발지역 수
    protection_zones: int = Field(ge=0)  # 노인보호구역 수
    overlaps: int = Field(ge=0)  # 사고다발지역·보호구역 경계 중첩 수
    accidents_per_10k: float = Field(ge=0)
    bar_percent: float = Field(ge=0)  # 막대 길이. 축 최댓값은 25건(1만 명당)
    rank: int = Field(ge=1)
    previous_rank: int = Field(ge=1)
    rank_change: int  # 전년 순위 - 올해 순위 (상승 +)
    rate_gap: float  # 서울 평균 대비 격차
    accidents_change: int
    accidents_change_percent: float | None  # 전년 사고가 0건이면 None


class DistrictRates(BaseModel):
    year: int
    previous_year: int
    seoul_accidents_per_10k: float
    districts: list[DistrictRate]

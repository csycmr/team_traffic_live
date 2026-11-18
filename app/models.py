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


class ElderlyDeathsByMode(BaseModel):
    """65세 이상 사망자의 사고 당시 상태(도넛 그래프). 그 외는 전체에서 뺀 값."""

    pedestrian: int = Field(ge=0)
    two_wheeler: int = Field(ge=0)
    car: int = Field(ge=0)
    bicycle: int = Field(ge=0)
    other: int = Field(ge=0)


class NationalDeathYear(BaseModel):
    """전국 교통사고 사망자(막대). 상태별 구분은 자료가 있는 연도(2020~2023)에만 채운다."""

    year: int
    total_deaths: int = Field(ge=0)
    elderly_deaths: int = Field(ge=0)
    elderly_share_percent: float = Field(ge=0, le=100)
    elderly_by_mode: ElderlyDeathsByMode | None = None


class NationalDeaths(BaseModel):
    years: list[NationalDeathYear]


class ElderlyPopulationPoint(BaseModel):
    """전국 65세 이상 주민등록인구(명). 기준 시점은 연·월 말이다."""

    year: int
    month: int = Field(ge=1, le=12)
    population: int = Field(gt=0)


class ElderlyPopulation(BaseModel):
    points: list[ElderlyPopulationPoint]


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


class ZoneBeforeAfterCase(BaseModel):
    district: str
    designated_year: int
    zones: int = Field(ge=1)  # 2025년 명단 기준 지정 구역 수
    accidents_before: int = Field(ge=0)  # 지정 전년도
    accidents_at: int = Field(ge=0)  # 지정연도
    accidents_after: int = Field(ge=0)  # 지정 이듬해
    accidents_change: int  # 이듬해 - 전년도
    rate_before: float = Field(ge=0)
    rate_at: float = Field(ge=0)
    rate_after: float = Field(ge=0)


class ZoneBeforeAfter(BaseModel):
    districts: int = Field(ge=0)
    increased: int = Field(ge=0)
    decreased: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    cases: list[ZoneBeforeAfterCase]


class ComparisonPoint(BaseModel):
    year: int
    population_65plus: int = Field(gt=0)
    accidents: int = Field(ge=0)
    accidents_per_10k: float = Field(ge=0)


class ComparisonSeries(BaseModel):
    name: str
    points: list[ComparisonPoint]


class DistrictComparison(BaseModel):
    years: list[int]
    series: list[ComparisonSeries]  # 서울 전체가 맨 앞, 그다음 비교 자치구


class Hotspot(BaseModel):
    id: str
    name: str
    district: str
    crashes: int = Field(ge=0)
    deaths: int = Field(ge=0)
    lat: float
    lng: float


class Hotspots(BaseModel):
    year: int
    locations: list[Hotspot]


class HotspotReviewItem(BaseModel):
    name: str  # 자치구 법정동 부근명
    district: str
    crashes: int = Field(ge=0)
    overlaps: bool  # 보호구역 경계와 겹침
    distance_m: int | None  # 겹치면 None, 아니면 가장 가까운 경계까지 직선거리


class HotspotDistrictCount(BaseModel):
    district: str
    overlapping: int = Field(ge=0)
    outside: int = Field(ge=0)


class HotspotCandidate(BaseModel):
    district: str
    selected: int = Field(ge=0)  # 선정 영역 수
    outside: int = Field(ge=0)
    overlapping: int = Field(ge=0)
    undetermined: int = Field(ge=0)
    accidents_per_10k: float = Field(ge=0)


class HotspotReview(BaseModel):
    year: int
    total: int = Field(ge=0)  # 판정 가능한 다발지역
    overlapping: int = Field(ge=0)
    outside: int = Field(ge=0)
    undetermined: int = Field(ge=0)
    outside_percent: float
    items: list[HotspotReviewItem]  # 사고 많은 순
    districts: list[HotspotDistrictCount]
    candidates: list[HotspotCandidate]


class ProtectionZone(BaseModel):
    id: str
    name: str
    district: str
    address: str
    lat: float
    lng: float
    data_date: str | None  # 경계 자료 기준일(YYYYMMDD)
    match_method: str | None  # 명단과 경계 자료를 잇는 방식
    note: str | None  # 위치 안내


class UnlocatedFacility(BaseModel):
    id: str
    name: str
    district: str
    address: str


class ProtectionZones(BaseModel):
    year: int
    total: int = Field(ge=0)  # 명단 시설 수
    facilities: list[ProtectionZone]  # 좌표가 있는 시설
    unlocated: list[UnlocatedFacility]  # 좌표가 없어 지도에서 주소로 찾아야 하는 시설


class ProtectionBoundary(BaseModel):
    facility_id: str
    wkt: str


class ProtectionBoundaries(BaseModel):
    zones: list[ProtectionBoundary]


class SchoolZone(BaseModel):
    name: str
    district: str
    road_address: str | None
    lot_address: str | None
    lat: float
    lng: float
    data_date: str | None


class SchoolZones(BaseModel):
    zones: list[SchoolZone]


class ZoneDensityGroup(BaseModel):
    population: int = Field(gt=0)
    zones: int = Field(gt=0)
    zones_per_10k: float = Field(ge=0)  # 인구 1만 명당 보호구역 수
    people_per_zone: int = Field(gt=0)  # 보호구역 1곳당 인구(반올림)


class ZoneOverview(BaseModel):
    population_month: str  # 인구 기준 연월
    child_zone_date: str  # 어린이보호구역 지정 현황 기준일
    elderly_year: int  # 노인보호구역 명단 연도
    child: ZoneDensityGroup  # 0~12세
    elderly: ZoneDensityGroup  # 65세 이상

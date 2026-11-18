"""FastAPI 통계 API. 화면과 기존 API는 아직 app/flask_app.py(Flask)가 제공한다."""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, load_settings
from app.errors import ServiceError
from app.models import (
    AccidentTrend,
    ChildCameraEffect,
    ChildPedestrian,
    DistrictComparison,
    DistrictRates,
    ElderlyPedestrian,
    ElderlyPopulation,
    HotspotReview,
    Hotspots,
    NationalDeaths,
    OecdRankings,
    ProtectionBoundaries,
    ProtectionZones,
    SchoolZones,
    ZoneBeforeAfter,
    ZoneBudget,
    ZoneOverview,
)
from app.services import (
    accident_service,
    budget_service,
    cctv_service,
    citydata_service,
    hotspot_service,
    comparison_service,
    oecd_service,
    population_service,
    protection_map_service,
    protection_service,
)

settings = get_settings()

app = FastAPI(title="서울 교통안전 라이브 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(request, error: ServiceError):
    return JSONResponse(status_code=error.status_code, content=error.payload())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/oecd/rankings", response_model=OecdRankings)
def get_oecd_rankings():
    return oecd_service.oecd_rankings()


@app.get("/api/traffic/accident-trend", response_model=AccidentTrend)
def get_accident_trend():
    return accident_service.accident_trend()


@app.get("/api/traffic/national-deaths", response_model=NationalDeaths)
def get_national_deaths():
    return accident_service.national_deaths()


@app.get("/api/traffic/child-pedestrian", response_model=ChildPedestrian)
def get_child_pedestrian(year: int = Query(2025)):
    return accident_service.child_pedestrian(year=year)


@app.get("/api/statistics/elderly", response_model=ElderlyPedestrian)
def get_elderly_pedestrian():
    return accident_service.elderly_pedestrian()


@app.get("/api/statistics/elderly/districts", response_model=DistrictRates)
def get_elderly_district_rates():
    return accident_service.elderly_district_rates()


@app.get("/api/statistics/elderly/zone-before-after", response_model=ZoneBeforeAfter)
def get_zone_before_after():
    return protection_service.zone_before_after()


@app.get("/api/statistics/elderly/district-comparison", response_model=DistrictComparison)
def get_district_comparison():
    return comparison_service.district_comparison()


@app.get("/api/protection-zones", response_model=ProtectionZones)
def get_protection_zones():
    return protection_map_service.protection_zones()


@app.get("/api/protection-zones/boundaries", response_model=ProtectionBoundaries)
def get_protection_boundaries():
    return protection_map_service.protection_boundaries()


@app.get("/api/school-zones", response_model=SchoolZones)
def get_school_zones():
    return protection_map_service.school_zones()


@app.get("/api/statistics/zone-overview", response_model=ZoneOverview)
def get_zone_overview():
    return protection_service.zone_overview()


@app.get("/api/traffic/child-camera-effect", response_model=ChildCameraEffect)
def get_child_camera_effect():
    return accident_service.child_camera_effect()


@app.get("/api/budget/zone-improvement", response_model=ZoneBudget)
def get_zone_budget():
    return budget_service.zone_budget()


@app.get("/api/statistics/hotspots", response_model=Hotspots)
def get_hotspots():
    return hotspot_service.hotspots()


@app.get("/api/statistics/hotspots/review", response_model=HotspotReview)
def get_hotspot_review():
    return hotspot_service.hotspot_review()


@app.get("/api/statistics/elderly-population", response_model=ElderlyPopulation)
def get_elderly_population():
    return population_service.elderly_population()


@app.get("/api/cctv")
def get_cctv():
    return cctv_service.seoul_cctv(load_settings().its_cctv_api_key)


@app.get("/api/citydata")
def get_citydata(place: str = Query("gwanghwamun")):
    current = load_settings()
    return citydata_service.citydata(
        place, current.seoul_citydata_api_key, current.citydata_cache_seconds
    )

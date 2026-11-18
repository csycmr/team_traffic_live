"""FastAPI 통계 API. 화면과 기존 API는 아직 app/flask_app.py(Flask)가 제공한다."""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, load_settings
from app.errors import ServiceError
from app.models import (
    AccidentTrend,
    ChildPedestrian,
    ElderlyPedestrian,
    OecdRankings,
)
from app.services import accident_service, cctv_service, citydata_service, oecd_service

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


@app.get("/api/traffic/child-pedestrian", response_model=ChildPedestrian)
def get_child_pedestrian(year: int = Query(2025)):
    return accident_service.child_pedestrian(year=year)


@app.get("/api/statistics/elderly", response_model=ElderlyPedestrian)
def get_elderly_pedestrian():
    return accident_service.elderly_pedestrian()


@app.get("/api/cctv")
def get_cctv():
    return cctv_service.seoul_cctv(load_settings().its_cctv_api_key)


@app.get("/api/citydata")
def get_citydata(place: str = Query("gwanghwamun")):
    current = load_settings()
    return citydata_service.citydata(
        place, current.seoul_citydata_api_key, current.citydata_cache_seconds
    )

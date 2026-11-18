"""서울시 도시데이터를 기존 뉴스룸 JSON 형식으로 바꾼다."""

import logging
import time
from xml.etree import ElementTree as ET

from app.adapters.citydata import fetch_citydata_xml
from app.errors import ServiceError

logger = logging.getLogger(__name__)

AREA_NAME = "광화문·덕수궁"
SUPPORTED_PLACE = "gwanghwamun"

_cache = {"expires_at": 0.0, "payload": None}


def clear_cache() -> None:
    _cache.update(expires_at=0.0, payload=None)


def citydata(
    place: str,
    api_key: str,
    cache_seconds: int = 60,
    fetcher=fetch_citydata_xml,
) -> dict:
    if place != SUPPORTED_PLACE:
        raise ServiceError("지원하지 않는 지역이야.", 400)

    if _cache["payload"] is not None and time.monotonic() < _cache["expires_at"]:
        return _cache["payload"]

    if not api_key:
        raise ServiceError("서울시 API 인증키가 설정되지 않았어.", 500)

    try:
        root = ET.fromstring(fetcher(api_key, AREA_NAME))

        if root.findtext(".//RESULT.CODE") != "INFO-000":
            raise ServiceError("서울시 도시데이터 조회 실패", 502)

        population = root.find(".//LIVE_PPLTN_STTS/LIVE_PPLTN_STTS")
        if population is None:
            raise ServiceError("실시간 인구 데이터가 없어.", 502)

        def read_number(tag):
            value = population.findtext(tag)
            return int(value) if value and value.isdigit() else None

        weather_data = root.find(".//WEATHER_STTS/WEATHER_STTS")

        def read_weather_number(tag):
            if weather_data is None:
                return None
            value = weather_data.findtext(tag)
            try:
                return float(value) if value else None
            except ValueError:
                return None

        payload = {
            "area": {"place": place, "name": AREA_NAME},
            "crowd": {
                "status": population.findtext("AREA_CONGEST_LVL"),
                "minPeople": read_number("AREA_PPLTN_MIN"),
                "maxPeople": read_number("AREA_PPLTN_MAX"),
                "updatedAt": population.findtext("PPLTN_TIME"),
            },
            "traffic": {
                "status": None,
                "averageSpeedKmh": None,
                "updatedAt": None,
                "slowSegments": [],
            },
            "weather": {
                "temperatureC": read_weather_number("TEMP"),
                "humidityPercent": read_weather_number("HUMIDITY"),
                "precipitationType": (
                    weather_data.findtext("PRECPT_TYPE")
                    if weather_data is not None
                    else None
                ),
            },
            "incidents": [],
        }
    except ServiceError:
        raise
    except (OSError, ET.ParseError, ValueError) as error:
        logger.error("서울시 도시데이터 조회 실패: %s", type(error).__name__)
        raise ServiceError("서울시 도시데이터를 가져오지 못했어.", 502) from error

    _cache["payload"] = payload
    _cache["expires_at"] = time.monotonic() + cache_seconds
    return payload

"""서울시 실시간 도시데이터(XML)를 기존 뉴스룸 JSON 형식으로 바꾼다.

"자료가 없다"와 "있는데 비어 있다"를 구분한다.
- 항목 자체가 응답에 없거나 값을 읽지 못하면 null (화면: '—', '정보 없음')
- 항목이 있고 내용이 비어 있으면 빈 배열 (화면: '알림 없음', '정체 구간 없음')
"""

import logging
import time
from xml.etree import ElementTree as ET

from app.adapters.citydata import fetch_citydata_xml
from app.errors import ServiceError

logger = logging.getLogger(__name__)

# 화면 선택 상자의 값 → 서울시 도시데이터 공식 지역명
PLACES = {
    "gwanghwamun": "광화문·덕수궁",
    "seoul-station": "서울역",
    "gangnam": "강남역",
    "dongdaemun": "동대문 관광특구",
    "namdaemun": "남대문시장",
}
MAX_SLOW_SEGMENTS = 10  # 화면에 보여 줄 서행·정체 구간 수(전체 개수는 따로 준다)
SLOW_STATUSES = ("정체", "서행")  # 정체가 더 나쁜 순서

_cache: dict[str, dict] = {}


def clear_cache() -> None:
    _cache.clear()


def _number(text: str | None) -> float | None:
    try:
        return float(text) if text and text.strip() else None
    except ValueError:
        return None


def _traffic(city: ET.Element) -> dict:
    section = city.find("ROAD_TRAFFIC_STTS")
    average = section.find("AVG_ROAD_DATA") if section is not None else None
    status = average.findtext("ROAD_TRAFFIC_IDX") if average is not None else None

    traffic = {
        "status": status or None,
        "averageSpeedKmh": (
            _number(average.findtext("ROAD_TRAFFIC_SPD")) if average is not None else None
        ),
        "updatedAt": (
            (average.findtext("ROAD_TRAFFIC_TIME") or None) if average is not None else None
        ),
        "slowSegments": None,
        "slowSegmentCount": None,
    }

    rows = section.findall("ROAD_TRAFFIC_STTS") if section is not None else []
    if not rows:
        return traffic  # 구간 자료가 없으니 '정체 없음'이 아니라 '정보 없음'이다.

    slow = []
    for row in rows:
        row_status = row.findtext("IDX")
        if row_status in SLOW_STATUSES:
            slow.append(
                {
                    "name": row.findtext("ROAD_NM") or None,
                    "start": row.findtext("START_ND_NM") or None,
                    "end": row.findtext("END_ND_NM") or None,
                    "speedKmh": _number(row.findtext("SPD")),
                    "status": row_status,
                }
            )

    # 정체 먼저, 같은 등급에서는 느린 구간 먼저. 속도를 모르면 맨 뒤로 보낸다.
    slow.sort(
        key=lambda item: (
            SLOW_STATUSES.index(item["status"]),
            item["speedKmh"] if item["speedKmh"] is not None else float("inf"),
        )
    )
    traffic["slowSegmentCount"] = len(slow)
    traffic["slowSegments"] = slow[:MAX_SLOW_SEGMENTS]
    return traffic


def _incidents(city: ET.Element) -> list | None:
    section = city.find("ACDNT_CNTRL_STTS")
    if section is None:
        return None  # 항목이 응답에 없으면 알 수 없다.

    incidents = []
    for row in section.findall("ACDNT_CNTRL_STTS"):
        # 원문은 줄바꿈 대신 '|'를 쓴다.
        detail = " ".join(
            part.strip() for part in (row.findtext("ACDNT_INFO") or "").split("|")
        ).strip()
        incidents.append(
            {
                "type": row.findtext("ACDNT_TYPE") or None,
                "subtype": row.findtext("ACDNT_DTYPE") or None,
                "occurredAt": row.findtext("ACDNT_OCCR_DT") or None,
                "detail": detail or None,
            }
        )
    return incidents  # 항목은 있는데 내용이 없으면 []


def _parse(xml: bytes, place: str, area_name: str) -> dict:
    root = ET.fromstring(xml)

    if root.findtext(".//RESULT.CODE") != "INFO-000":
        raise ServiceError("서울시 도시데이터 조회 실패", 502)

    city = root.find(".//CITYDATA")
    if city is None:
        raise ServiceError(f"{area_name} 도시데이터가 없어.", 502)

    population = city.find("LIVE_PPLTN_STTS/LIVE_PPLTN_STTS")
    if population is None:
        raise ServiceError("실시간 인구 데이터가 없어.", 502)

    def read_number(tag):
        value = population.findtext(tag)
        return int(value) if value and value.isdigit() else None

    weather_data = city.find("WEATHER_STTS/WEATHER_STTS")

    def read_weather_number(tag):
        return _number(weather_data.findtext(tag)) if weather_data is not None else None

    return {
        "area": {"place": place, "name": area_name},
        "crowd": {
            "status": population.findtext("AREA_CONGEST_LVL"),
            "minPeople": read_number("AREA_PPLTN_MIN"),
            "maxPeople": read_number("AREA_PPLTN_MAX"),
            "updatedAt": population.findtext("PPLTN_TIME"),
        },
        "traffic": _traffic(city),
        "weather": {
            "temperatureC": read_weather_number("TEMP"),
            "humidityPercent": read_weather_number("HUMIDITY"),
            "precipitationType": (
                weather_data.findtext("PRECPT_TYPE") if weather_data is not None else None
            ),
        },
        "incidents": _incidents(city),
    }


def citydata(
    place: str,
    api_key: str,
    cache_seconds: int = 60,
    fetcher=fetch_citydata_xml,
) -> dict:
    area_name = PLACES.get(place)
    if area_name is None:
        raise ServiceError("지원하지 않는 지역이야.", 400)

    cached = _cache.get(place)
    if cached and time.monotonic() < cached["expires_at"]:
        return cached["payload"]

    if not api_key:
        raise ServiceError("서울시 API 인증키가 설정되지 않았어.", 500)

    try:
        payload = _parse(fetcher(api_key, area_name), place, area_name)
    except ServiceError:
        raise
    except (OSError, ET.ParseError, ValueError) as error:
        logger.error("서울시 도시데이터 조회 실패: %s", type(error).__name__)
        raise ServiceError("서울시 도시데이터를 가져오지 못했어.", 502) from error

    _cache[place] = {"payload": payload, "expires_at": time.monotonic() + cache_seconds}
    return payload

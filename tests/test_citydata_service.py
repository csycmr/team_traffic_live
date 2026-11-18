from pathlib import Path

import pytest

from app.errors import ServiceError
from app.services import citydata_service

XML = """<?xml version="1.0" encoding="UTF-8"?>
<SeoulRtd.citydata>
  <RESULT><RESULT.CODE>INFO-000</RESULT.CODE></RESULT>
  <CITYDATA>
    <LIVE_PPLTN_STTS><LIVE_PPLTN_STTS>
      <AREA_CONGEST_LVL>보통</AREA_CONGEST_LVL>
      <AREA_PPLTN_MIN>1000</AREA_PPLTN_MIN>
      <AREA_PPLTN_MAX>1200</AREA_PPLTN_MAX>
      <PPLTN_TIME>2026-11-18 11:00</PPLTN_TIME>
    </LIVE_PPLTN_STTS></LIVE_PPLTN_STTS>
    <WEATHER_STTS><WEATHER_STTS>
      <TEMP>7.5</TEMP><HUMIDITY>40</HUMIDITY><PRECPT_TYPE>없음</PRECPT_TYPE>
    </WEATHER_STTS></WEATHER_STTS>
  </CITYDATA>
</SeoulRtd.citydata>"""


FIXTURES = Path(__file__).parent / "fixtures"


def real_xml(place: str) -> bytes:
    """실제 응답(2026-11-18 12:30)에서 교통·돌발·날씨만 남기고 줄인 샘플."""
    return (FIXTURES / f"citydata_{place}.xml").read_bytes()


@pytest.fixture(autouse=True)
def fresh_cache():
    citydata_service.clear_cache()
    yield
    citydata_service.clear_cache()


def test_unsupported_place_is_400():
    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("busan", "key", fetcher=lambda *a: XML)
    assert error.value.status_code == 400


def test_missing_key_is_500():
    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("gwanghwamun", "", fetcher=lambda *a: XML)
    assert error.value.status_code == 500


def test_parses_payload_and_caches():
    calls = []

    def fetch(key, area):
        calls.append(area)
        return XML

    first = citydata_service.citydata("gwanghwamun", "key", 60, fetcher=fetch)
    second = citydata_service.citydata("gwanghwamun", "key", 60, fetcher=fetch)

    assert calls == ["광화문·덕수궁"]
    assert second is first
    assert first["crowd"] == {
        "status": "보통",
        "minPeople": 1000,
        "maxPeople": 1200,
        "updatedAt": "2026-11-18 11:00",
    }
    assert first["weather"]["temperatureC"] == 7.5
    # 이 XML에는 교통·돌발 항목이 아예 없다. '없음'이 아니라 '알 수 없음'(null)이어야 한다.
    assert first["traffic"]["status"] is None
    assert first["traffic"]["slowSegments"] is None
    assert first["incidents"] is None


def test_upstream_failure_codes():
    bad_code = XML.replace("INFO-000", "ERROR-500")
    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: bad_code)
    assert error.value.status_code == 502

    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: b"<not xml")
    assert error.value.status_code == 502


def test_real_gwanghwamun_traffic_and_incidents():
    data = citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: real_xml("gwanghwamun"))
    traffic = data["traffic"]
    assert (traffic["status"], traffic["averageSpeedKmh"]) == ("정체", 13.0)
    assert traffic["updatedAt"] == "2026-11-18 12:30"

    segments = traffic["slowSegments"]
    assert len(segments) == citydata_service.MAX_SLOW_SEGMENTS
    assert traffic["slowSegmentCount"] >= len(segments)
    assert {item["status"] for item in segments} <= {"정체", "서행"}
    speeds = [item["speedKmh"] for item in segments]
    assert speeds == sorted(speeds)  # 정체 구간 안에서 느린 순서
    assert segments[0]["name"] and segments[0]["start"] and segments[0]["end"]

    assert len(data["incidents"]) == 2
    first = data["incidents"][0]
    assert (first["type"], first["subtype"], first["occurredAt"]) == (
        "집회및행사", "행사", "2026-11-18 11:00",
    )
    assert "|" not in first["detail"] and first["detail"].startswith("[통제] 덕수궁길")


def test_real_seoul_station_has_no_incidents_but_is_known():
    """항목은 있는데 비어 있으면 빈 배열이다. null과 달라야 화면이 '알림 없음'을 보여 준다."""
    data = citydata_service.citydata("seoul-station", "key", fetcher=lambda *a: real_xml("seoul-station"))
    assert data["incidents"] == []
    assert data["area"] == {"place": "seoul-station", "name": "서울역"}
    assert data["traffic"]["status"] == "서행"


def test_no_slow_segments_is_empty_list_not_null():
    xml = real_xml("gwanghwamun").decode().replace("<IDX>정체</IDX>", "<IDX>원활</IDX>").replace(
        "<IDX>서행</IDX>", "<IDX>원활</IDX>"
    )
    data = citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: xml.encode())
    assert data["traffic"]["slowSegments"] == []
    assert data["traffic"]["slowSegmentCount"] == 0


def test_all_five_places_use_official_area_names():
    seen = []

    def fetch(key, area):
        seen.append(area)
        return real_xml("seoul-station")

    for place in citydata_service.PLACES:
        citydata_service.citydata(place, "key", fetcher=fetch)
    assert seen == ["광화문·덕수궁", "서울역", "강남역", "동대문 관광특구", "남대문시장"]


def test_cache_is_per_place():
    calls = []

    def fetch(key, area):
        calls.append(area)
        return real_xml("seoul-station")

    citydata_service.citydata("seoul-station", "key", 60, fetcher=fetch)
    citydata_service.citydata("gangnam", "key", 60, fetcher=fetch)
    citydata_service.citydata("seoul-station", "key", 60, fetcher=fetch)
    assert calls == ["서울역", "강남역"]

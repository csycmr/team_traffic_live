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
    assert first["traffic"]["slowSegments"] == []


def test_upstream_failure_codes():
    bad_code = XML.replace("INFO-000", "ERROR-500")
    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: bad_code)
    assert error.value.status_code == 502

    with pytest.raises(ServiceError) as error:
        citydata_service.citydata("gwanghwamun", "key", fetcher=lambda *a: b"<not xml")
    assert error.value.status_code == 502

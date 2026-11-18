"""서울시 실시간 도시데이터(XML) API."""

from urllib.parse import quote
from urllib.request import urlopen

CITYDATA_URL = "http://openapi.seoul.go.kr:8088"


def fetch_citydata_xml(api_key: str, area_name: str) -> bytes:
    url = f"{CITYDATA_URL}/{api_key}/xml/citydata/1/5/{quote(area_name)}"
    with urlopen(url, timeout=15) as response:
        return response.read()

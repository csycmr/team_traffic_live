"""국가교통정보센터(ITS) CCTV 목록 API."""

import json
from urllib.parse import urlencode
from urllib.request import urlopen

ITS_URL = "https://openapi.its.go.kr:9443/cctvInfo"


def fetch_cameras(key, outer_ring):
    longitudes, latitudes = zip(*outer_ring)
    query = urlencode(
        {
            "apiKey": key,
            "type": "its",
            "cctvType": "1",
            "minX": min(longitudes),
            "maxX": max(longitudes),
            "minY": min(latitudes),
            "maxY": max(latitudes),
            "getType": "json",
        }
    )
    with urlopen(f"{ITS_URL}?{query}", timeout=20) as response:
        payload = json.load(response)

    result = payload["response"]
    cameras = result.get("data")
    if cameras is None and str(result.get("datacount")) == "0":
        return []
    if not isinstance(cameras, list):
        raise ValueError("CCTV 목록 형식을 확인할 수 없어.")
    return cameras

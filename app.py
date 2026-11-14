"""Serve the traffic dashboard and its Seoul CCTV feed."""

import json
import math
import os
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ITS_URL = "https://openapi.its.go.kr:9443/cctvInfo"
app = Flask(__name__, static_folder=None)


@lru_cache(maxsize=1)
def seoul_boundary():
    source = DATA / "08_서울_자치구_경계.geojson"
    with source.open(encoding="utf-8-sig") as file:
        features = json.load(file)["features"]
    for feature in features:
        if feature["properties"]["자치구명"] == "서울 전체":
            geometry = feature["geometry"]
            if geometry["type"] == "Polygon":
                return geometry["coordinates"]
    raise ValueError("서울 전체 경계를 찾을 수 없어.")


def inside_ring(x, y, ring):
    inside = False
    previous_x, previous_y = ring[-1]
    for current_x, current_y in ring:
        cross = (x - previous_x) * (current_y - previous_y) - (
            y - previous_y
        ) * (current_x - previous_x)
        if (
            abs(cross) < 1e-12
            and min(current_x, previous_x) <= x <= max(current_x, previous_x)
            and min(current_y, previous_y) <= y <= max(current_y, previous_y)
        ):
            return True
        if (current_y > y) != (previous_y > y):
            intersection = current_x + (y - current_y) * (
                previous_x - current_x
            ) / (previous_y - current_y)
            if x < intersection:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


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


@app.get("/")
def dashboard():
    return send_from_directory(ROOT, "seoul-traffic-demo.html")


@app.get("/data/<path:filename>")
def dashboard_data(filename):
    return send_from_directory(DATA, filename)


@app.get("/api/cctv")
def cctv():
    key = os.environ.get("ITS_CCTV_API_KEY", "").strip()
    if not key:
        return jsonify(error="ITS_CCTV_API_KEY 환경변수를 설정해 줘."), 503

    try:
        outer_ring, *holes = seoul_boundary()
    except (OSError, ValueError, KeyError, TypeError):
        return jsonify(error="서울시 경계 파일을 확인해 줘."), 500

    try:
        cameras = fetch_cameras(key, outer_ring)
    except HTTPError as error:
        return jsonify(error="국가교통정보센터 요청 실패", upstream_status=error.code), 502
    except (URLError, TimeoutError, ValueError, KeyError, TypeError):
        return jsonify(error="국가교통정보센터 응답을 읽지 못했어."), 502

    seoul_cameras = []
    for camera in cameras:
        if not isinstance(camera, dict):
            continue
        try:
            longitude = float(camera["coordx"])
            latitude = float(camera["coordy"])
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            continue
        if inside_ring(longitude, latitude, outer_ring) and not any(
            inside_ring(longitude, latitude, hole) for hole in holes
        ):
            seoul_cameras.append(
                {
                    "cctvname": camera.get("cctvname"),
                    "coordx": longitude,
                    "coordy": latitude,
                    "cctvurl": camera.get("cctvurl"),
                    "cctvformat": camera.get("cctvformat"),
                }
            )

    return jsonify(
        source_count=len(cameras),
        seoul_count=len(seoul_cameras),
        cameras=seoul_cameras,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

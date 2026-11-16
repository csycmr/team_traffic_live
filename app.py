"""Serve the traffic dashboard and its Seoul CCTV feed."""

import json
import math
import os
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from dotenv import load_dotenv

from flask import Flask, jsonify, send_from_directory
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ITS_URL = "https://openapi.its.go.kr:9443/cctvInfo"
load_dotenv(dotenv_path=ROOT / ".env")
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


@app.get("/assets/<path:filename>")
def dashboard_asset(filename):
    return send_from_directory(ROOT / "assets", filename)


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


@app.get("/api/statistics/elderly")
def elderly_statistics():
    """2025년 서울 고령 보행자 교통사고 통계 제공."""

    csv_path = DATA / "01_자치구연도_패널.csv"

    try:
        df = pd.read_csv(csv_path)

        # 2025년 자료만 선택
        data_2025 = df[df["사고연도"] == 2025]

        # 데이터 유효성 검사
        if data_2025["자치구명"].nunique() != 25:
            return jsonify(
                error="2025년 서울 25개 자치구 자료를 확인할 수 없어."
            ), 500

        # 사고·사망·부상 통계 합산
        columns = {
            "accidents": "고령보행자_사고건수",
            "deaths": "고령보행자_사망자수",
            "injuries": "고령보행자_부상자수",
        }

        if data_2025[list(columns.values())].isna().any().any():
            return jsonify(
                error="사고 통계에 누락된 값이 있어."
            ), 500

        totals = {
            key: int(data_2025[column].sum())
            for key, column in columns.items()
        }

        return jsonify(
            year=2025,
            region="서울",
            districts=25,
            **totals,
        )

    except (OSError, ValueError, KeyError) as error:
        return jsonify(error=str(error)), 500


@app.get("/api/citydata")
def citydata():
    """서울시 실시간 도시데이터를 기존 뉴스룸 JSON 형식으로 제공."""
    from flask import request
    from urllib.parse import quote

    place = request.args.get("place", "gwanghwamun")

    if place != "gwanghwamun":
        return jsonify(error="지원하지 않는 지역이야."), 400

    api_key = os.getenv("SEOUL_CITYDATA_API_KEY")

    if not api_key:
        return jsonify(error="서울시 API 인증키가 설정되지 않았어."), 500

    area_name = "\uad11\ud654\ubb38\u00b7\ub355\uc218\uad81"
    encoded_area = quote(area_name)

    url = (
        "http://openapi.seoul.go.kr:8088/"
        f"{api_key}/xml/citydata/1/5/{encoded_area}"
    )

    try:
        with urlopen(url, timeout=15) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        result_code = root.findtext(".//RESULT.CODE")

        if result_code != "INFO-000":
            return jsonify(error="서울시 도시데이터 조회 실패"), 502

        population = root.find(".//LIVE_PPLTN_STTS/LIVE_PPLTN_STTS")

        if population is None:
            return jsonify(error="실시간 인구 데이터가 없어."), 502

        def read_number(tag):
            value = population.findtext(tag)
            return int(value) if value and value.isdigit() else None

        crowd = {
            "status": population.findtext("AREA_CONGEST_LVL"),
            "minPeople": read_number("AREA_PPLTN_MIN"),
            "maxPeople": read_number("AREA_PPLTN_MAX"),
            "updatedAt": population.findtext("PPLTN_TIME"),
        }

        return jsonify(
            area={
                "place": place,
                "name": area_name,
            },
            crowd=crowd,
            traffic={
                "status": None,
                "averageSpeedKmh": None,
                "updatedAt": None,
                "slowSegments": [],
            },
            weather={
                "temperatureC": None,
                "humidityPercent": None,
                "precipitationType": None,
            },
            incidents=[],
        )

    except (OSError, ET.ParseError, ValueError) as error:
        app.logger.error("서울시 도시데이터 조회 실패: %s", type(error).__name__)
        return jsonify(error="서울시 도시데이터를 가져오지 못했어."), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

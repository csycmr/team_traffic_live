"""서울시 경계 GeoJSON과 점-다각형 판정."""

import json
from functools import lru_cache
from pathlib import Path

from app.services.data_files import BOUNDARY_FILE, resolve_data_dir


@lru_cache(maxsize=4)
def _boundary_from(path: str):
    with Path(path).open(encoding="utf-8-sig") as file:
        features = json.load(file)["features"]
    for feature in features:
        if feature["properties"]["자치구명"] == "서울 전체":
            geometry = feature["geometry"]
            if geometry["type"] == "Polygon":
                return geometry["coordinates"]
    raise ValueError("서울 전체 경계를 찾을 수 없어.")


def seoul_boundary(data_dir: Path | str | None = None):
    """서울 전체 Polygon 좌표. 첫 고리가 바깥 경계, 나머지는 구멍이야."""
    return _boundary_from(str(resolve_data_dir(data_dir) / BOUNDARY_FILE))


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

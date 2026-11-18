"""서울시 경계 안의 CCTV만 골라 돌려준다."""

import math
from pathlib import Path
from urllib.error import HTTPError, URLError

from app.adapters.cctv import fetch_cameras
from app.errors import ServiceError
from app.services.boundary_service import inside_ring, seoul_boundary


def seoul_cctv(
    api_key: str,
    data_dir: Path | str | None = None,
    fetcher=fetch_cameras,
) -> dict:
    if not api_key:
        raise ServiceError("ITS_CCTV_API_KEY 환경변수를 설정해 줘.", 503)

    try:
        outer_ring, *holes = seoul_boundary(data_dir)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ServiceError("서울시 경계 파일을 확인해 줘.", 500) from error

    try:
        cameras = fetcher(api_key, outer_ring)
    except HTTPError as error:
        raise ServiceError(
            "국가교통정보센터 요청 실패", 502, upstream_status=error.code
        ) from error
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
        raise ServiceError("국가교통정보센터 응답을 읽지 못했어.", 502) from error

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

    return {
        "source_count": len(cameras),
        "seoul_count": len(seoul_cameras),
        "cameras": seoul_cameras,
    }

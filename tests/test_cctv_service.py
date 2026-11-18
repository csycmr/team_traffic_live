from urllib.error import HTTPError

import pytest

from app.errors import ServiceError
from app.services import cctv_service


def camera(name, x, y):
    return {"cctvname": name, "coordx": x, "coordy": y, "cctvurl": "u", "cctvformat": "HLS"}


def test_missing_key_is_503():
    with pytest.raises(ServiceError) as error:
        cctv_service.seoul_cctv("", fetcher=lambda *a: [])
    assert error.value.status_code == 503


def test_filters_to_seoul_boundary(real_data_dir):
    cameras = [
        camera("시청", "126.9780", "37.5665"),
        camera("수원", "127.0286", "37.2636"),
        camera("좌표없음", "x", "y"),
        {"cctvname": "좌표키없음"},
        "문자열",
    ]
    result = cctv_service.seoul_cctv("key", real_data_dir, fetcher=lambda *a: cameras)
    assert result["source_count"] == 5
    assert result["seoul_count"] == 1
    assert result["cameras"][0]["cctvname"] == "시청"
    assert result["cameras"][0]["coordx"] == 126.978


def test_upstream_http_error_keeps_status(real_data_dir):
    def fail(*args):
        raise HTTPError("http://x", 429, "limit", None, None)

    with pytest.raises(ServiceError) as error:
        cctv_service.seoul_cctv("key", real_data_dir, fetcher=fail)
    assert error.value.status_code == 502
    assert error.value.payload()["upstream_status"] == 429


def test_bad_upstream_payload_is_502(real_data_dir):
    def bad(*args):
        raise ValueError("형식")

    with pytest.raises(ServiceError) as error:
        cctv_service.seoul_cctv("key", real_data_dir, fetcher=bad)
    assert error.value.status_code == 502

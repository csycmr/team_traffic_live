import pytest

# newsroom 패키지가 쓰는 라이브러리가 없으면 건너뛴다.
for module in ("flask", "sqlalchemy", "feedparser", "openai"):
    pytest.importorskip(module)

from app import flask_app  # noqa: E402
from app.errors import ServiceError  # noqa: E402


@pytest.fixture
def client():
    return flask_app.app.test_client()


def test_dashboard_and_data_files_are_served(client):
    assert client.get("/").status_code == 200
    csv = client.get("/data/15_TAAS_시도시군구_교통사고_2020-2025.csv")
    assert csv.status_code == 200
    assert b"193889" in csv.data


def test_elderly_statistics(client):
    body = client.get("/api/statistics/elderly").get_json()
    assert (body["year"], body["accidents"], body["deaths"]) == (2025, 2060, 82)


def test_service_error_becomes_json(client, monkeypatch):
    def fail(*args, **kwargs):
        raise ServiceError("테스트 오류", 502, upstream_status=429)

    monkeypatch.setattr(flask_app.cctv_service, "seoul_cctv", fail)
    response = client.get("/api/cctv")
    assert response.status_code == 502
    assert response.get_json() == {"error": "테스트 오류", "upstream_status": 429}


def test_citydata_rejects_unknown_place(client):
    response = client.get("/api/citydata?place=busan")
    assert response.status_code == 400

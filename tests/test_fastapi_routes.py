import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_accident_trend_endpoint():
    years = client.get("/api/traffic/accident-trend").json()["years"]
    assert len(years) == 6
    assert years[-1] == {
        "year": 2025,
        "nationwide_accidents": 193889,
        "seoul_accidents": 34309,
        "seoul_injuries": 45446,
        "seoul_deaths": 212,
    }


def test_child_pedestrian_endpoint():
    assert client.get("/api/traffic/child-pedestrian").json() == {
        "year": 2025,
        "accidents": 339,
        "deaths": 1,
    }


def test_oecd_rankings_endpoint():
    years = client.get("/api/oecd/rankings").json()["years"]
    assert [year["year"] for year in years] == [2020, 2021, 2022, 2023]


def test_elderly_endpoint_matches_flask_shape():
    body = client.get("/api/statistics/elderly").json()
    assert set(body) == {"year", "region", "districts", "accidents", "deaths", "injuries"}


def test_service_error_uses_error_key():
    response = client.get("/api/traffic/child-pedestrian", params={"year": 1999})
    assert response.status_code == 500
    assert "error" in response.json()


def test_cors_allows_dashboard_origin():
    response = client.get(
        "/health", headers={"Origin": "http://127.0.0.1:5001"}
    )
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5001"

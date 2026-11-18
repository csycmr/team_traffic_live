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
        "nationwide_deaths": 2549,
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
    assert {"year", "region", "districts", "accidents", "deaths", "injuries"} <= set(body)
    assert body["accidents_per_10k"] == 10.77
    assert body["death_share_percent"] == 67.2


def test_service_error_uses_error_key():
    response = client.get("/api/traffic/child-pedestrian", params={"year": 1999})
    assert response.status_code == 500
    assert "error" in response.json()


def test_cors_allows_dashboard_origin():
    response = client.get(
        "/health", headers={"Origin": "http://127.0.0.1:5001"}
    )
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5001"


def test_elderly_districts_endpoint():
    body = client.get("/api/statistics/elderly/districts").json()
    assert body["seoul_accidents_per_10k"] == 10.77
    assert len(body["districts"]) == 25
    assert body["districts"][0]["district"] == "중구"


def test_national_deaths_endpoint():
    years = client.get("/api/traffic/national-deaths").json()["years"]
    assert years[0] == {
        "year": 2020,
        "total_deaths": 3081,
        "elderly_deaths": 1342,
        "elderly_share_percent": 43.6,
        "elderly_by_mode": {
            "pedestrian": 628,
            "two_wheeler": 274,
            "car": 131,
            "bicycle": 122,
            "other": 187,
        },
    }
    assert years[-1]["elderly_deaths"] == 1378
    assert years[-1]["elderly_by_mode"] is None

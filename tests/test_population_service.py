import pytest

from app.errors import ServiceError
from app.services import population_service
from app.services.data_files import ELDERLY_POPULATION_FILE

HEADER = "기준연월,65세이상_인구수"


def test_sorts_and_splits_period(write_csv):
    data_dir = write_csv(
        ELDERLY_POPULATION_FILE, f"{HEADER}\n2026-10,300\n2022-12,100\n2023-12,200"
    )
    points = population_service.elderly_population(data_dir).points
    assert [(p.year, p.month, p.population) for p in points] == [
        (2022, 12, 100),
        (2023, 12, 200),
        (2026, 10, 300),
    ]


@pytest.mark.parametrize("period", ["2022/12", "202212", "2022-13", "2022-1"])
def test_bad_period_is_error(write_csv, period):
    data_dir = write_csv(ELDERLY_POPULATION_FILE, f"{HEADER}\n{period},100")
    with pytest.raises(ServiceError, match="YYYY-MM"):
        population_service.elderly_population(data_dir)


def test_duplicate_period_is_error(write_csv):
    data_dir = write_csv(ELDERLY_POPULATION_FILE, f"{HEADER}\n2022-12,100\n2022-12,101")
    with pytest.raises(ServiceError, match="겹쳐"):
        population_service.elderly_population(data_dir)


def test_blank_value_is_error(write_csv):
    data_dir = write_csv(ELDERLY_POPULATION_FILE, f"{HEADER}\n2022-12,")
    with pytest.raises(ServiceError, match="비어"):
        population_service.elderly_population(data_dir)


def test_missing_file_is_service_error(tmp_path):
    with pytest.raises(ServiceError):
        population_service.elderly_population(tmp_path)


def test_real_data_matches_chart_values():
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[1] / "data"
    points = population_service.elderly_population(data_dir).points
    assert [(p.year, p.month, p.population) for p in points] == [
        (2022, 12, 9267290),
        (2023, 12, 9730411),
        (2024, 12, 10256782),
        (2025, 12, 10840822),
        (2026, 10, 11350255),
    ]

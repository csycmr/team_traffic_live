import pytest

from app.errors import ServiceError
from app.services import accident_service
from app.services.data_files import ACCIDENT_TREND_FILE, CHILD_SUMMARY_FILE

CHILD_HEADER = "자료구분,지역,사고연도,연령범위,사고건수,사망자수,부상자수"


def test_accident_trend_real_data_ends_with_2025(real_data_dir):
    years = accident_service.accident_trend(real_data_dir).years
    assert [row.year for row in years] == [2020, 2021, 2022, 2023, 2024, 2025]
    last = years[-1]
    assert (last.nationwide_accidents, last.seoul_accidents) == (193889, 34309)
    assert (last.seoul_injuries, last.seoul_deaths) == (45446, 212)


def test_accident_trend_sorts_by_year(write_csv):
    data_dir = write_csv(
        ACCIDENT_TREND_FILE,
        "year,nationwide_accidents,seoul_accidents,seoul_injuries,seoul_deaths\n"
        "2021,2,2,2,2\n2020,1,1,1,1",
    )
    assert [row.year for row in accident_service.accident_trend(data_dir).years] == [
        2020,
        2021,
    ]


def test_accident_trend_missing_column_is_error(write_csv):
    data_dir = write_csv(ACCIDENT_TREND_FILE, "year,nationwide_accidents\n2020,1")
    with pytest.raises(ServiceError):
        accident_service.accident_trend(data_dir)


def test_child_pedestrian_real_data(real_data_dir):
    child = accident_service.child_pedestrian(real_data_dir)
    assert (child.year, child.accidents, child.deaths) == (2025, 339, 1)


def test_child_pedestrian_requires_exactly_one_row(write_csv):
    row = "보행자 교통사고,서울,2025,12세 이하,10,1,9"
    data_dir = write_csv(CHILD_SUMMARY_FILE, f"{CHILD_HEADER}\n{row}\n{row}")
    with pytest.raises(ServiceError, match="2개"):
        accident_service.child_pedestrian(data_dir)

    data_dir = write_csv(CHILD_SUMMARY_FILE, f"{CHILD_HEADER}\n{row}")
    assert accident_service.child_pedestrian(data_dir).accidents == 10


def test_child_pedestrian_ignores_other_rows(write_csv):
    rows = [
        "보행자 교통사고,서울,2025,65세 이상,,82,",
        "보행자 교통사고,서울,2025,12세 이하,339,1,344",
        "보행자 교통사고,서울,2024,12세 이하,300,2,310",
    ]
    data_dir = write_csv(CHILD_SUMMARY_FILE, CHILD_HEADER + "\n" + "\n".join(rows))
    child = accident_service.child_pedestrian(data_dir)
    assert (child.accidents, child.deaths) == (339, 1)


def test_child_pedestrian_blank_value_is_error(write_csv):
    data_dir = write_csv(
        CHILD_SUMMARY_FILE, f"{CHILD_HEADER}\n보행자 교통사고,서울,2025,12세 이하,,1,"
    )
    with pytest.raises(ServiceError, match="비어"):
        accident_service.child_pedestrian(data_dir)


def test_elderly_pedestrian_real_data(real_data_dir):
    elderly = accident_service.elderly_pedestrian(real_data_dir)
    assert (elderly.districts, elderly.accidents, elderly.deaths) == (25, 2060, 82)


def test_elderly_rates_and_year_change(real_data_dir):
    """화면 카드: 1만 명당 10.77건, 전체 보행 사망자 중 67.2%, 전년 대비 +97건·+14명."""
    elderly = accident_service.elderly_pedestrian(real_data_dir)
    assert elderly.population_65plus == 1912751
    assert elderly.accidents_per_10k == 10.77
    assert (elderly.all_pedestrian_deaths, elderly.death_share_percent) == (122, 67.2)
    assert elderly.previous_year == 2024
    assert (elderly.accidents_change, elderly.deaths_change) == (97, 14)


def test_elderly_pedestrian_needs_previous_year(real_data_dir):
    with pytest.raises(ServiceError, match="25개 자치구"):
        accident_service.elderly_pedestrian(real_data_dir, year=2019)


def test_missing_file_is_service_error(tmp_path):
    with pytest.raises(ServiceError):
        accident_service.accident_trend(tmp_path)

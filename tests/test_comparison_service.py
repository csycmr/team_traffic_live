import pytest

from app.errors import ServiceError
from app.services import comparison_service
from app.services.data_files import PANEL_FILE

HEADER = "사고연도,자치구명,고령인구,고령보행자_사고건수\n"


def panel_text(rows_for_a=None, districts=25):
    lines = []
    for year in (2024, 2025):
        for i in range(districts):
            name = "가구" if i == 0 else f"구{i}"
            lines.append(f"{year},{name},1000,{10 + i}")
    return HEADER + "\n".join(lines)


def test_series_start_with_seoul_total(write_csv):
    data_dir = write_csv(PANEL_FILE, panel_text())
    result = comparison_service.district_comparison(data_dir, districts=("가구",))
    assert result.years == [2024, 2025]
    seoul, gu = result.series
    assert seoul.name == "서울 전체"
    assert seoul.points[0].population_65plus == 25000
    assert seoul.points[0].accidents == sum(10 + i for i in range(25))
    assert gu.name == "가구"
    assert (gu.points[0].accidents, gu.points[0].accidents_per_10k) == (10, 100.0)


def test_unknown_district_is_error(write_csv):
    data_dir = write_csv(PANEL_FILE, panel_text())
    with pytest.raises(ServiceError, match="전부 있지"):
        comparison_service.district_comparison(data_dir, districts=("없는구",))


def test_not_25_districts_is_error(write_csv):
    data_dir = write_csv(PANEL_FILE, panel_text(districts=24))
    with pytest.raises(ServiceError, match="25개"):
        comparison_service.district_comparison(data_dir, districts=("가구",))


def test_blank_value_is_error(write_csv):
    text = panel_text().replace("2025,가구,1000,10", "2025,가구,1000,")
    data_dir = write_csv(PANEL_FILE, text)
    with pytest.raises(ServiceError, match="비어"):
        comparison_service.district_comparison(data_dir, districts=("가구",))


def test_real_data_matches_page(real_data_dir):
    result = comparison_service.district_comparison(real_data_dir)
    got = {
        s.name: [(p.year, p.population_65plus, p.accidents, p.accidents_per_10k) for p in s.points]
        for s in result.series
    }
    assert [s.name for s in result.series] == ["서울 전체", "동대문구", "도봉구"]
    assert got["서울 전체"] == [
        (2022, 1667411, 1846, 11.07), (2023, 1743696, 1973, 11.32),
        (2024, 1824895, 1963, 10.76), (2025, 1912751, 2060, 10.77),
    ]
    assert got["동대문구"] == [
        (2022, 64468, 138, 21.41), (2023, 67030, 155, 23.12),
        (2024, 69582, 130, 18.68), (2025, 72779, 132, 18.14),
    ]
    assert got["도봉구"] == [
        (2022, 66998, 49, 7.31), (2023, 70436, 61, 8.66),
        (2024, 74223, 61, 8.22), (2025, 78335, 38, 4.85),
    ]

import pytest

from app.errors import ServiceError
from app.services import protection_service
from app.services.data_files import PANEL_FILE, PROTECTION_MASTER_FILE

MASTER = "시설ID,자치구명,지정연도,명단2025\n"
PANEL = "자치구명,사고연도,고령인구,고령보행자_사고건수\n"


def write_both(write_csv, master_rows, panel_rows):
    data_dir = write_csv(PROTECTION_MASTER_FILE, MASTER + master_rows)
    (data_dir / PANEL_FILE).write_text(PANEL + panel_rows + "\n", encoding="utf-8-sig")
    return data_dir


def panel(gu, counts, population=1000):
    return "\n".join(
        f"{gu},{year},{population},{n}" for year, n in zip((2022, 2023, 2024, 2025), counts)
    )


def test_groups_zones_by_district_and_year(write_csv):
    master = "Z1,가구,2023,1\nZ2,가구,2023,1\nZ3,가구,2023,0\nZ4,나구,2024,1"
    rows = panel("가구", (10, 20, 15, 30)) + "\n" + panel("나구", (5, 5, 5, 8))
    result = protection_service.zone_before_after(write_both(write_csv, master, rows))
    cases = {(c.district, c.designated_year): c for c in result.cases}
    first = cases[("가구", 2023)]
    assert first.zones == 2  # 명단2025가 0인 구역은 세지 않는다
    assert (first.accidents_before, first.accidents_at, first.accidents_after) == (10, 20, 15)
    assert first.accidents_change == 5
    assert (first.rate_before, first.rate_at, first.rate_after) == (100.0, 200.0, 150.0)
    assert (result.increased, result.decreased, result.unchanged) == (2, 0, 0)
    assert result.districts == 2


def test_orders_by_year_then_largest_change(write_csv):
    master = "Z1,가구,2023,1\nZ2,나구,2023,1\nZ3,다구,2024,1"
    rows = "\n".join(
        [
            panel("가구", (10, 10, 10, 10)),
            panel("나구", (10, 10, 30, 10)),
            panel("다구", (5, 5, 5, 1)),
        ]
    )
    cases = protection_service.zone_before_after(write_both(write_csv, master, rows)).cases
    assert [(c.district, c.designated_year) for c in cases] == [
        ("나구", 2023),
        ("가구", 2023),
        ("다구", 2024),
    ]


def test_years_without_before_or_after_are_left_out(write_csv):
    master = "Z1,가구,2022,1\nZ2,가구,2025,1\nZ3,가구,2024,1"
    rows = panel("가구", (1, 2, 3, 4))
    cases = protection_service.zone_before_after(write_both(write_csv, master, rows)).cases
    assert [c.designated_year for c in cases] == [2024]


def test_no_cases_is_error(write_csv):
    data_dir = write_both(write_csv, "Z1,가구,2019,1", panel("가구", (1, 2, 3, 4)))
    with pytest.raises(ServiceError, match="사례"):
        protection_service.zone_before_after(data_dir)


def test_blank_panel_value_is_error(write_csv):
    rows = "가구,2022,1000,5\n가구,2023,1000,\n가구,2024,1000,7\n가구,2025,1000,8"
    data_dir = write_both(write_csv, "Z1,가구,2023,1", rows)
    with pytest.raises(ServiceError, match="비어"):
        protection_service.zone_before_after(data_dir)


def test_real_data_matches_page_table(real_data_dir):
    result = protection_service.zone_before_after(real_data_dir)
    rows = [
        (c.district, c.designated_year, c.zones, c.accidents_before, c.accidents_at,
         c.accidents_after, c.accidents_change, c.rate_before, c.rate_at, c.rate_after)
        for c in result.cases
    ]
    assert rows == [
        ("은평구", 2023, 1, 78, 112, 111, 33, 8.70, 11.94, 11.32),
        ("송파구", 2023, 4, 102, 121, 116, 14, 9.85, 11.11, 10.15),
        ("관악구", 2023, 1, 78, 75, 82, 4, 9.46, 8.78, 9.23),
        ("마포구", 2023, 1, 40, 46, 38, -2, 7.15, 7.95, 6.33),
        ("노원구", 2024, 1, 82, 85, 85, 3, 8.50, 8.45, 8.11),
        ("서초구", 2024, 2, 52, 47, 54, 2, 7.92, 6.84, 7.47),
        ("관악구", 2024, 1, 75, 82, 75, 0, 8.78, 9.23, 8.07),
        ("송파구", 2024, 6, 121, 116, 110, -11, 11.11, 10.15, 9.22),
        ("동대문구", 2024, 1, 155, 130, 132, -23, 23.12, 18.68, 18.14),
    ]
    assert (result.districts, result.increased, result.decreased, result.unchanged) == (7, 5, 3, 1)

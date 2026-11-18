import pytest

from app.errors import ServiceError
from app.services import accident_service
from app.services.data_files import (
    ACCIDENT_TREND_FILE,
    CHILD_SUMMARY_FILE,
    OECD_FILE,
)

CHILD_HEADER = "자료구분,지역,사고연도,연령범위,사고건수,사망자수,부상자수"


TAAS_HEADER = "연도,시도,시군구,사고건수,사망자수,부상자수"


def test_accident_trend_real_data_ends_with_2025(real_data_dir):
    years = accident_service.accident_trend(real_data_dir).years
    assert [row.year for row in years] == [2020, 2021, 2022, 2023, 2024, 2025]
    last = years[-1]
    assert (last.nationwide_accidents, last.nationwide_deaths) == (193889, 2549)
    assert (last.seoul_accidents, last.seoul_injuries, last.seoul_deaths) == (34309, 45446, 212)
    assert [row.nationwide_deaths for row in years] == [3081, 2916, 2735, 2551, 2521, 2549]


def test_accident_trend_uses_total_rows_and_sorts(write_csv):
    rows = [
        "2021,합계,합계,20,2,30",
        "2021,서울,합계,5,1,6",
        "2021,서울,종로구,5,1,6",
        "2020,서울,합계,4,1,5",
        "2020,합계,합계,10,1,15",
    ]
    data_dir = write_csv(ACCIDENT_TREND_FILE, TAAS_HEADER + "\n" + "\n".join(rows))
    years = accident_service.accident_trend(data_dir).years
    assert [row.year for row in years] == [2020, 2021]
    assert (years[1].nationwide_accidents, years[1].seoul_accidents) == (20, 5)


def test_accident_trend_missing_column_is_error(write_csv):
    data_dir = write_csv(ACCIDENT_TREND_FILE, "연도,시도\n2020,합계")
    with pytest.raises(ServiceError):
        accident_service.accident_trend(data_dir)


def test_accident_trend_duplicate_total_is_error(write_csv):
    row = "2020,서울,합계,4,1,5"
    data_dir = write_csv(ACCIDENT_TREND_FILE, f"{TAAS_HEADER}\n{row}\n{row}\n2020,합계,합계,9,1,9")
    with pytest.raises(ServiceError, match="하나가 아니야"):
        accident_service.accident_trend(data_dir)


def test_seoul_districts_sum_to_seoul_total(real_data_dir):
    """원본 xlsx 검증: 서울 25개 구 합이 서울 합계 행과 같다."""
    import pandas as pd

    data = pd.read_csv(real_data_dir / ACCIDENT_TREND_FILE, encoding="utf-8-sig")
    seoul = data[data["시도"].eq("서울")]
    for year, group in seoul.groupby("연도"):
        total = group[group["시군구"].eq("합계")].iloc[0]
        districts = group[~group["시군구"].eq("합계")]
        assert len(districts) == 25
        assert districts["사고건수"].sum() == total["사고건수"]
        assert districts["사망자수"].sum() == total["사망자수"]


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


def test_district_rates_real_data(real_data_dir):
    result = accident_service.elderly_district_rates(real_data_dir)
    assert (result.year, result.previous_year, result.seoul_accidents_per_10k) == (
        2025,
        2024,
        10.77,
    )
    rows = result.districts
    assert len(rows) == 25
    assert [row.rank for row in rows] == sorted(row.rank for row in rows)

    first, second = rows[0], rows[1]
    assert (first.district, first.accidents_per_10k, first.rank, first.previous_rank) == (
        "중구",
        22.08,
        1,
        1,
    )
    assert (first.population_65plus, first.accidents, first.hotspots) == (27623, 61, 2)
    assert (first.protection_zones, first.overlaps, first.bar_percent) == (8, 1, 88.33)
    assert (second.district, second.rank_change, second.rate_gap) == ("동대문구", 1, 7.37)
    assert (second.accidents_change, second.accidents_change_percent) == (2, 1.5)

    geumcheon = next(row for row in rows if row.district == "금천구")
    assert (geumcheon.rank, geumcheon.previous_rank, geumcheon.rank_change) == (4, 10, 6)
    assert (geumcheon.accidents_change, geumcheon.accidents_change_percent) == (29, 53.7)


def test_district_rates_weighted_average_matches_card(real_data_dir):
    """자치구 표의 서울 평균은 고령 사고율 카드(10.77)와 같은 값이어야 한다."""
    districts = accident_service.elderly_district_rates(real_data_dir)
    elderly = accident_service.elderly_pedestrian(real_data_dir)
    assert districts.seoul_accidents_per_10k == elderly.accidents_per_10k
    assert sum(row.accidents for row in districts.districts) == elderly.accidents


def test_national_deaths_real_data(real_data_dir):
    """화면 막대: 전체 3,081→2,549명, 65세 이상은 OECD 2020~2023만."""
    years = accident_service.national_deaths(real_data_dir).years
    assert [row.year for row in years] == [2020, 2021, 2022, 2023, 2024, 2025]
    assert [row.total_deaths for row in years] == [3081, 2916, 2735, 2551, 2521, 2549]
    assert [row.elderly_deaths for row in years[:4]] == [1342, 1295, 1258, 1240]
    assert [row.elderly_share_percent for row in years[:4]] == [43.6, 44.4, 46.0, 48.6]
    assert all(
        row.elderly_deaths is None and row.elderly_share_percent is None
        for row in years[4:]
    )


def test_national_deaths_total_mismatch_is_error(write_csv, tmp_path):
    taas = "연도,시도,시군구,사고건수,사망자수,부상자수\n"
    taas += "2020,합계,합계,10,100,15\n2020,서울,합계,4,1,5"
    oecd = "국가,연도,전체_사망자수,65세이상_사망자수\n대한민국,2020,99,40"
    (tmp_path / ACCIDENT_TREND_FILE).write_text(taas, encoding="utf-8-sig")
    (tmp_path / OECD_FILE).write_text(oecd, encoding="utf-8-sig")
    with pytest.raises(ServiceError, match="달라"):
        accident_service.national_deaths(tmp_path)

import pytest

from app.errors import ServiceError
from app.services import protection_service
from app.services.data_files import (
    CHILD_ZONE_FILE,
    PROTECTION_MASTER_FILE,
    SEOUL_POPULATION_FILE,
)


def write_all(tmp_path, people, child="기준일,지역,기재항목합계\n2026-06-30,서울,10\n2026-06-30,부산,99\n"):
    header = "기준연월,지역,연령,총인구수\n"
    (tmp_path / SEOUL_POPULATION_FILE).write_text(header + people, encoding="utf-8-sig")
    (tmp_path / CHILD_ZONE_FILE).write_text(child, encoding="utf-8-sig")
    (tmp_path / PROTECTION_MASTER_FILE).write_text(
        "시설ID,명단2025\nZ1,1\nZ1,1\nZ2,1\nZ3,0\n", encoding="utf-8-sig"
    )
    return tmp_path


PEOPLE = (
    "2026-09,서울특별시,0세,50\n2026-09,서울특별시,12세,50\n2026-09,서울특별시,13세,999\n"
    "2026-09,서울특별시,64세,999\n2026-09,서울특별시,65세,300\n2026-09,서울특별시,100세 이상,101\n"
)


def test_groups_children_0_to_12_and_elderly_65_plus(tmp_path):
    result = protection_service.zone_overview(write_all(tmp_path, PEOPLE))
    assert (result.child.population, result.child.zones) == (100, 10)
    assert result.child.zones_per_10k == 1000.0 and result.child.people_per_zone == 10
    assert (result.elderly.population, result.elderly.zones) == (401, 2)  # 같은 시설ID는 한 곳
    assert result.elderly.people_per_zone == 201  # 200.5는 올린다
    assert (result.population_month, result.child_zone_date) == ("2026-09", "2026-06-30")


def test_two_months_is_error(tmp_path):
    with pytest.raises(ServiceError, match="기준연월"):
        protection_service.zone_overview(write_all(tmp_path, PEOPLE + "2026-08,서울특별시,1세,5\n"))


def test_missing_seoul_row_is_error(tmp_path):
    with pytest.raises(ServiceError, match="서울"):
        protection_service.zone_overview(write_all(tmp_path, PEOPLE, "기준일,지역,기재항목합계\n2026-06-30,부산,9\n"))


def test_real_data_matches_page(real_data_dir):
    result = protection_service.zone_overview(real_data_dir)
    assert (result.child.population, result.child.zones) == (648419, 1630)
    assert (result.elderly.population, result.elderly.zones) == (1965896, 195)
    assert round(result.child.zones_per_10k, 2) == 25.14 and round(result.elderly.zones_per_10k, 2) == 0.99
    assert (result.child.people_per_zone, result.elderly.people_per_zone) == (398, 10082)
    assert round(result.child.zones_per_10k / 30 * 100, 4) == 83.7936
    assert round(result.elderly.zones_per_10k / 30 * 100, 4) == 3.3064

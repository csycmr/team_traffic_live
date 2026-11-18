import pytest

from app.errors import ServiceError
from app.services import budget_service
from app.services.data_files import BUDGET_FILE, CHILD_LIST_FILES, PROTECTION_MASTER_FILE

HEADER = "PDF쪽,구분,행유형,항목,2025예산_천원,2026예산_천원\n"


def write_list(tmp_path, date, count, written_date=None):
    lines = "".join(f"{written_date or date},가구,시설{i}\n" for i in range(count))
    (tmp_path / CHILD_LIST_FILES[date]).write_text("기준일,자치구,시설명\n" + lines, encoding="utf-8-sig")


def write(tmp_path, rows):
    (tmp_path / BUDGET_FILE).write_text(HEADER + rows, encoding="utf-8-sig")
    (tmp_path / PROTECTION_MASTER_FILE).write_text("시설ID,명단2025\nZ1,1\nZ1,1\nZ2,1\nZ3,0\n", encoding="utf-8-sig")
    write_list(tmp_path, "2025-12-31", 50)
    write_list(tmp_path, "2026-06-30", 40)
    return tmp_path


ROWS = (
    '616,세출예산,연도별 예산 비교,어린이 보호구역 개선(전환사업),1000,500\n'
    '616,세출예산,연도별 예산 비교,"노인· 장애인 보호구역 개선(전환사업)",300,100\n'
    '1850,명시이월 사업조서,원문,어린이 보호구역 개선(전환사업),,\n'
)


def test_rows_are_found_ignoring_spaces_and_other_sections(tmp_path):
    result = budget_service.zone_budget(write(tmp_path, ROWS))
    assert (result.pdf_page, result.child.budget_2025, result.child.budget_2026) == (616, 1000, 500)
    assert result.elderly_disabled.name == "노인· 장애인 보호구역 개선(전환사업)"
    assert result.elderly_disabled.zones_2025 == 2  # 같은 시설ID는 한 곳
    assert (result.elderly_disabled.per_zone_2025_man_won, result.elderly_disabled.per_zone_2026_man_won) == (15, 5)
    assert (result.child.zones_2025, result.child.zones_2026) == (50, 40)
    assert (result.child.per_zone_2025_man_won, result.child.per_zone_2026_man_won) == (2, 1)  # 1.0e6/50 원=2만, 0.5e6/40 원=1.25만


def test_missing_project_is_error(tmp_path):
    with pytest.raises(ServiceError, match="정확히 하나"):
        budget_service.zone_budget(write(tmp_path, ROWS.split("\n")[0] + "\n"))


def test_list_with_other_date_is_error(tmp_path):
    data_dir = write(tmp_path, ROWS)
    write_list(data_dir, "2025-12-31", 50, written_date="2026-06-30")
    with pytest.raises(ServiceError, match="기준일"):
        budget_service.zone_budget(data_dir)


def test_missing_list_file_is_error(tmp_path):
    data_dir = write(tmp_path, ROWS)
    (data_dir / CHILD_LIST_FILES["2026-06-30"]).unlink()
    with pytest.raises(ServiceError, match="읽지 못했어|없어"):
        budget_service.zone_budget(data_dir)


def test_duplicate_project_is_error(tmp_path):
    dup = '616,세출예산,연도별 예산 비교,어린이 보호구역 개선(전환사업),1,1\n'
    with pytest.raises(ServiceError, match="정확히 하나"):
        budget_service.zone_budget(write(tmp_path, ROWS + dup))


def test_real_data_matches_page(real_data_dir):
    result = budget_service.zone_budget(real_data_dir)
    assert result.pdf_page == 616
    # 화면: 237.23억 / 182.71억 / 18.64억 / 10.63억
    assert [round(v / 100000, 2) for v in (
        result.child.budget_2025, result.child.budget_2026,
        result.elderly_disabled.budget_2025, result.elderly_disabled.budget_2026)] == [237.23, 182.71, 18.64, 10.63]
    assert (result.child.zones_2025, result.child.zones_2026) == (1658, 1630)
    assert (result.child.per_zone_2025_man_won, result.child.per_zone_2026_man_won) == (1431, 1121)
    assert result.elderly_disabled.zones_2025 == result.elderly_disabled.zones_2026 == 195
    assert (result.elderly_disabled.per_zone_2025_man_won, result.elderly_disabled.per_zone_2026_man_won) == (956, 545)

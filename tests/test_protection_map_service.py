import pytest

from app.errors import ServiceError
from app.services import protection_map_service
from app.services.data_files import PROTECTION_BOUNDARY_FILE, PROTECTION_MASTER_FILE, SCHOOL_ZONE_FILE

MASTER = "시설ID,시설명,자치구명,위치,명단2025\n"
BOUNDARY = "시설ID,위도,경도,명단매칭방식,데이터기준일,경계WKT\n"
SCHOOL = "시설명,자치구명,도로명주소,지번주소,위도,경도,데이터기준일\n"


def write(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8-sig")


def setup(tmp_path, master, boundary):
    write(tmp_path, PROTECTION_MASTER_FILE, MASTER + master)
    write(tmp_path, PROTECTION_BOUNDARY_FILE, BOUNDARY + boundary)
    return tmp_path


def test_best_boundary_wins_and_unlocated_are_listed(tmp_path):
    data_dir = setup(
        tmp_path,
        "Z001,가경로당,가구,가길 1,1\nZ002,나경로당,나구,나길,1\nZ003,다경로당,다구,다길,0\nZ186,시장,동대문구,왕산로33길,1\n",
        "Z001,37.5,127.0,유사명(검수필요),20240101,W1\n"
        "Z001,37.6,127.1,주소+시설명,20200101,W2\n"  # 매칭이 더 좋음
        "Z001,37.7,127.2,주소+시설명,20230101,W3\n"  # 같은 매칭이면 더 최근
        "Z001,37.8,127.3,주소+시설명,20230101,W4\n"  # 날짜가 같으면 먼저 나온 것
        "Z001,0,0,주소+시설명,20990101,W5\n",  # 서울 밖 좌표는 건너뜀
    )
    result = protection_map_service.protection_zones(data_dir)
    assert result.total == 3  # 명단2025가 1인 시설만
    a, market = result.facilities
    assert (a.id, a.lat, a.lng, a.data_date, a.match_method) == ("Z001", 37.7, 127.2, "20230101", "주소+시설명")
    assert market.id == "Z186" and market.note and market.data_date is None
    assert [u.id for u in result.unlocated] == ["Z002"]


def test_duplicate_master_rows_count_once(tmp_path):
    data_dir = setup(tmp_path, "Z001,가,가구,길,1\nZ001,가,가구,길,1\n", "Z001,37.5,127.0,주소+시설명,20240101,W\n")
    assert protection_map_service.protection_zones(data_dir).total == 1


def test_missing_master_value_is_error(tmp_path):
    data_dir = setup(tmp_path, "Z001,,가구,길,1\n", "")
    with pytest.raises(ServiceError, match="빈 행"):
        protection_map_service.protection_zones(data_dir)


def test_boundaries_return_every_row(tmp_path):
    data_dir = setup(tmp_path, "Z001,가,가구,길,1\n", "Z001,37.5,127.0,주소+시설명,20240101,W1\nZ001,37.5,127.0,주소+시설명,20240101,W2\n")
    assert [(z.facility_id, z.wkt) for z in protection_map_service.protection_boundaries(data_dir).zones] == [("Z001", "W1"), ("Z001", "W2")]


def test_school_zones_skip_outside_seoul_and_keep_nulls(tmp_path):
    write(
        tmp_path, SCHOOL_ZONE_FILE,
        SCHOOL + "가초,가구,가길 1,,37.5,127.0,2023-01-18\n나초,나구,,나동 2,0,0,2023-01-18\n",
    )
    zones = protection_map_service.school_zones(tmp_path).zones
    assert len(zones) == 1
    assert (zones[0].name, zones[0].road_address, zones[0].lot_address, zones[0].data_date) == ("가초", "가길 1", None, "2023-01-18")


def test_real_data_counts(real_data_dir):
    zones = protection_map_service.protection_zones(real_data_dir)
    assert (zones.total, len(zones.facilities), len(zones.unlocated)) == (195, 180, 15)
    assert len(protection_map_service.protection_boundaries(real_data_dir).zones) == 280
    assert len(protection_map_service.school_zones(real_data_dir).zones) == 1601

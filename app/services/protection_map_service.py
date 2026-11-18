"""지도에 그릴 노인보호구역·보호구역 경계·어린이보호구역 자료."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import (
    ProtectionBoundaries,
    ProtectionBoundary,
    ProtectionZone,
    ProtectionZones,
    SchoolZone,
    SchoolZones,
    UnlocatedFacility,
)
from app.services.data_files import (
    PROTECTION_BOUNDARY_FILE,
    PROTECTION_MASTER_FILE,
    SCHOOL_ZONE_FILE,
    read_csv,
    require_columns,
)

# 경계 자료에도 없고 주소로도 못 찾는 시설의 손으로 확인한 대표 위치
MANUAL_LOCATIONS = {
    "Z186": (37.580216, 127.042424, "시장 대표 위치 · 보호구역 경계와 다를 수 있어"),
}
MASTER_COLUMNS = ["시설ID", "시설명", "자치구명", "위치", "명단2025"]
BOUNDARY_COLUMNS = ["시설ID", "위도", "경도", "명단매칭방식", "데이터기준일", "경계WKT"]
SCHOOL_COLUMNS = ["시설명", "자치구명", "도로명주소", "지번주소", "위도", "경도", "데이터기준일"]


def _in_seoul(lat, lng) -> bool:
    return pd.notna(lat) and pd.notna(lng) and 37 <= lat <= 38 and 126 <= lng <= 128


def _text(value) -> str | None:
    return None if pd.isna(value) else str(value)


def _match_rank(method) -> int:
    """검수가 필요한 매칭은 가장 낮게, 주소와 시설명이 모두 맞으면 가장 높게 본다."""

    if isinstance(method, str) and "검수필요" in method:
        return 0
    return 2 if method == "주소+시설명" else 1


def protection_zones(data_dir: Path | str | None = None, year: int = 2025) -> ProtectionZones:
    """명단(해당 연도) 시설마다 가장 믿을 만한 경계 한 곳의 좌표를 고른다."""

    master = read_csv(PROTECTION_MASTER_FILE, data_dir)
    boundary = read_csv(PROTECTION_BOUNDARY_FILE, data_dir)
    require_columns(master, PROTECTION_MASTER_FILE, MASTER_COLUMNS)
    require_columns(boundary, PROTECTION_BOUNDARY_FILE, BOUNDARY_COLUMNS)
    column = f"명단{year}"
    if column not in master.columns:
        raise ServiceError(f"{PROTECTION_MASTER_FILE}에 {column} 열이 없어.", 500)

    # 같은 시설ID는 위치는 처음 나온 자리, 내용은 마지막 행을 쓴다.
    facilities: dict[str, object] = {}
    for row in master[master[column] == 1].itertuples():
        if pd.isna(row.시설ID) or pd.isna(row.시설명) or pd.isna(row.자치구명):
            raise ServiceError(f"{PROTECTION_MASTER_FILE}에 시설ID·시설명·자치구명이 빈 행이 있어.", 500)
        facilities[row.시설ID] = row
    if not facilities:
        raise ServiceError(f"{PROTECTION_MASTER_FILE}에 {year}년 명단 시설이 없어.", 500)

    best: dict[str, object] = {}
    for row in boundary.itertuples():
        if not _in_seoul(row.위도, row.경도):
            continue
        previous = best.get(row.시설ID)
        if (
            previous is None
            or _match_rank(row.명단매칭방식) > _match_rank(previous.명단매칭방식)
            or (
                _match_rank(row.명단매칭방식) == _match_rank(previous.명단매칭방식)
                and row.데이터기준일 > previous.데이터기준일
            )
        ):
            best[row.시설ID] = row

    located: list[ProtectionZone] = []
    unlocated: list[UnlocatedFacility] = []
    for facility_id, facility in facilities.items():
        address = "" if pd.isna(facility.위치) else str(facility.위치)
        chosen = best.get(facility_id)
        if chosen is not None:
            date = None if pd.isna(chosen.데이터기준일) else str(int(chosen.데이터기준일))
            located.append(
                ProtectionZone(
                    id=facility_id, name=facility.시설명, district=facility.자치구명, address=address,
                    lat=float(chosen.위도), lng=float(chosen.경도), data_date=date,
                    match_method=_text(chosen.명단매칭방식), note=None,
                )
            )
        elif facility_id in MANUAL_LOCATIONS:
            lat, lng, note = MANUAL_LOCATIONS[facility_id]
            located.append(
                ProtectionZone(
                    id=facility_id, name=facility.시설명, district=facility.자치구명, address=address,
                    lat=lat, lng=lng, data_date=None, match_method=None, note=note,
                )
            )
        else:
            unlocated.append(
                UnlocatedFacility(id=facility_id, name=facility.시설명, district=facility.자치구명, address=address)
            )

    return ProtectionZones(year=year, total=len(facilities), facilities=located, unlocated=unlocated)


def protection_boundaries(data_dir: Path | str | None = None) -> ProtectionBoundaries:
    """지도에 그릴 보호구역 경계 폴리곤(WKT) 전체."""

    boundary = read_csv(PROTECTION_BOUNDARY_FILE, data_dir)
    require_columns(boundary, PROTECTION_BOUNDARY_FILE, ["시설ID", "경계WKT"])
    if boundary["경계WKT"].isna().any() or boundary["시설ID"].isna().any():
        raise ServiceError(f"{PROTECTION_BOUNDARY_FILE}에 시설ID나 경계가 빈 행이 있어.", 500)
    return ProtectionBoundaries(
        zones=[ProtectionBoundary(facility_id=row.시설ID, wkt=row.경계WKT) for row in boundary.itertuples()]
    )


def school_zones(data_dir: Path | str | None = None) -> SchoolZones:
    """서울 어린이보호구역 시설 중 좌표가 서울 안에 있는 곳."""

    data = read_csv(SCHOOL_ZONE_FILE, data_dir)
    require_columns(data, SCHOOL_ZONE_FILE, SCHOOL_COLUMNS)
    zones = [
        SchoolZone(
            name=row.시설명, district=row.자치구명, road_address=_text(row.도로명주소),
            lot_address=_text(row.지번주소), lat=float(row.위도), lng=float(row.경도),
            data_date=_text(row.데이터기준일),
        )
        for row in data.itertuples()
        if _in_seoul(row.위도, row.경도) and pd.notna(row.시설명) and pd.notna(row.자치구명)
    ]
    if not zones:
        raise ServiceError(f"{SCHOOL_ZONE_FILE}에 서울 안의 시설이 없어.", 500)
    return SchoolZones(zones=zones)

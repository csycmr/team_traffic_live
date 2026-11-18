"""사고다발지역과 노인보호구역 경계 중첩 자료."""

import math
import re
from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import (
    Hotspot,
    HotspotCandidate,
    HotspotDistrictCount,
    Hotspots,
    HotspotReview,
    HotspotReviewItem,
)
from app.services.data_files import (
    HOTSPOT_FILE,
    HOTSPOT_LINK_FILE,
    PANEL_FILE,
    read_csv,
    require_columns,
)

CANDIDATE_DISTRICTS = ("동대문구", "중랑구", "은평구", "금천구")  # 화면의 현장 검토 후보 예시
HOTSPOT_COLUMNS = [
    "다발지역FID", "사고연도", "자치구코드", "자치구명", "법정동명", "부근명",
    "지점명", "사고건수", "사망자수", "경도", "위도",
]
LINK_COLUMNS = ["다발지역FID", "사고연도", "최단거리_m", "경계중첩"]


def _hotspot_rows(data_dir, year: int) -> pd.DataFrame:
    data = read_csv(HOTSPOT_FILE, data_dir)
    require_columns(data, HOTSPOT_FILE, HOTSPOT_COLUMNS)
    rows = data[data["사고연도"] == year]
    if rows.empty:
        raise ServiceError(f"{HOTSPOT_FILE}에 {year}년 사고다발지역이 없어.", 500)
    if rows["다발지역FID"].duplicated().any():
        raise ServiceError(f"{HOTSPOT_FILE}에 같은 다발지역FID가 겹쳐 있어.", 500)
    if rows[HOTSPOT_COLUMNS].isna().any().any():
        raise ServiceError(f"{HOTSPOT_FILE}의 {year}년 값에 비어 있는 칸이 있어.", 500)
    return rows


def hotspots(data_dir: Path | str | None = None, year: int = 2025) -> Hotspots:
    """지도에 점으로 찍을 사고다발지역. 자치구코드, 다발지역FID 순서."""

    rows = _hotspot_rows(data_dir, year).sort_values(["자치구코드", "다발지역FID"])
    return Hotspots(
        year=year,
        locations=[
            Hotspot(
                id=str(row.다발지역FID),
                name=row.지점명.replace("서울특별시", "서울", 1),
                district=row.자치구명,
                crashes=int(row.사고건수),
                deaths=int(row.사망자수),
                lat=float(row.위도),
                lng=float(row.경도),
            )
            for row in rows.itertuples()
        ],
    )


def _meters(value: float) -> int:
    """0.5는 내려서 정수 m로 만든다. (335.5 → 335)"""

    return int(math.ceil(value - 0.5))


NEARBY_SUFFIX = re.compile(r"\s*부근$")


def _label(row) -> str:
    return " ".join([row.자치구명, row.법정동명, NEARBY_SUFFIX.sub("", str(row.부근명))])


def hotspot_review(
    data_dir: Path | str | None = None,
    year: int = 2025,
    candidates: tuple[str, ...] = CANDIDATE_DISTRICTS,
) -> HotspotReview:
    """사고다발지역을 보호구역 경계와 비교한 목록·자치구별 막대·후보 표."""

    spots = _hotspot_rows(data_dir, year)
    links = read_csv(HOTSPOT_LINK_FILE, data_dir)
    require_columns(links, HOTSPOT_LINK_FILE, LINK_COLUMNS)
    links = links[links["사고연도"] == year]
    if links["다발지역FID"].duplicated().any():
        raise ServiceError(f"{HOTSPOT_LINK_FILE}에 같은 다발지역FID가 겹쳐 있어.", 500)

    merged = spots.merge(links[["다발지역FID", "최단거리_m", "경계중첩"]], on="다발지역FID", how="left")
    if len(merged) != len(spots):
        raise ServiceError("다발지역과 보호구역 연결표의 행 수가 달라.", 500)

    undetermined = merged["경계중첩"].isna()
    judged = merged[~undetermined]
    overlapping_mask = judged["경계중첩"].eq(1)
    if not set(judged["경계중첩"].unique()) <= {0, 1}:
        raise ServiceError(f"{HOTSPOT_LINK_FILE}의 경계중첩은 0 또는 1이어야 해.", 500)
    if judged["최단거리_m"].isna().any():
        raise ServiceError(f"{HOTSPOT_LINK_FILE}에 최단거리가 비어 있는 판정 행이 있어.", 500)

    ordered = judged.sort_values(
        ["사고건수", "최단거리_m", "자치구코드", "다발지역FID"],
        ascending=[False, True, True, True],
    )
    items = [
        HotspotReviewItem(
            name=_label(row),
            district=row.자치구명,
            crashes=int(row.사고건수),
            overlaps=bool(row.경계중첩 == 1),
            distance_m=None if row.경계중첩 == 1 else _meters(float(row.최단거리_m)),
        )
        for row in ordered.itertuples()
    ]

    overlapping = int(overlapping_mask.sum())
    outside = int((~overlapping_mask).sum())
    total = overlapping + outside

    per_district = (
        merged.assign(
            inside=merged["경계중첩"].eq(1).astype(int),
            out=merged["경계중첩"].eq(0).astype(int),
        )
        .groupby(["자치구코드", "자치구명"], as_index=False)
        .agg(inside=("inside", "sum"), out=("out", "sum"))
    )
    per_district["total"] = per_district["inside"] + per_district["out"]
    per_district = per_district[per_district["total"] > 0].sort_values(
        ["total", "inside", "자치구코드"], ascending=[False, False, True]
    )
    districts = [
        HotspotDistrictCount(district=row.자치구명, overlapping=int(row.inside), outside=int(row.out))
        for row in per_district.itertuples()
    ]

    panel = read_csv(PANEL_FILE, data_dir)
    require_columns(panel, PANEL_FILE, ["사고연도", "자치구명", "고령인구", "고령보행자_사고건수"])
    panel = panel[panel["사고연도"] == year].set_index("자치구명")
    picked = []
    for name in candidates:
        mine = merged[merged["자치구명"] == name]
        if mine.empty or name not in panel.index:
            raise ServiceError(f"{name}의 {year}년 다발지역·사고 자료가 없어.", 500)
        accidents = panel.at[name, "고령보행자_사고건수"]
        population = panel.at[name, "고령인구"]
        if pd.isna(accidents) or pd.isna(population) or population <= 0:
            raise ServiceError(f"{name}의 {year}년 사고·인구 값이 비어 있어.", 500)
        picked.append(
            HotspotCandidate(
                district=name,
                selected=len(mine),
                outside=int(mine["경계중첩"].eq(0).sum()),
                overlapping=int(mine["경계중첩"].eq(1).sum()),
                undetermined=int(mine["경계중첩"].isna().sum()),
                accidents_per_10k=round(float(accidents / population * 10000), 2),
            )
        )

    return HotspotReview(
        year=year,
        total=total,
        overlapping=overlapping,
        outside=outside,
        undetermined=int(undetermined.sum()),
        outside_percent=round(outside / total * 100, 1) if total else 0.0,
        items=items,
        districts=districts,
        candidates=picked,
    )

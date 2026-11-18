"""서울시 2026년 예산서의 보호구역 개선 세부사업 편성액."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import BudgetProject, ZoneBudget
from app.services.data_files import (
    BUDGET_FILE,
    CHILD_LIST_FILES,
    PROTECTION_MASTER_FILE,
    read_csv,
    require_columns,
)

COLUMNS = ["PDF쪽", "구분", "행유형", "항목", "2025예산_천원", "2026예산_천원"]
CHILD_NAME = "어린이보호구역개선(전환사업)"
ELDERLY_NAME = "노인·장애인보호구역개선(전환사업)"
ELDERLY_ZONE_YEAR = 2025


def _project_row(budget: pd.DataFrame, name: str) -> pd.Series:
    """공백을 뺀 항목명이 같은 세출예산 '연도별 예산 비교' 행은 정확히 하나여야 한다."""

    key = budget["항목"].astype(str).str.replace(r"\s+", "", regex=True)
    rows = budget[budget["구분"].eq("세출예산") & budget["행유형"].eq("연도별 예산 비교") & key.eq(name)]
    if len(rows) != 1:
        raise ServiceError(f"{BUDGET_FILE}에서 '{name}' 행이 정확히 하나여야 하는데 {len(rows)}개야.", 500)
    row = rows.iloc[0]
    if pd.isna(row["2025예산_천원"]) or pd.isna(row["2026예산_천원"]):
        raise ServiceError(f"{BUDGET_FILE}의 '{name}' 예산 값이 비어 있어.", 500)
    return row


def _man_won(thousand_won: int, zones: int) -> int:
    """천원 단위 예산을 구역 수로 나눠 만 원 단위로 반올림한다."""

    return int(thousand_won * 1000 / zones / 10000 + 0.5)


def _child_zones(data_dir, date: str) -> int:
    """연말 기준일의 서울 어린이보호구역 지정 목록 행 수(시설 한 곳이 한 줄)."""

    name = CHILD_LIST_FILES.get(date)
    if name is None:
        raise ServiceError(f"{date} 어린이보호구역 지정 목록 파일이 설정에 없어.", 500)
    data = read_csv(name, data_dir)
    require_columns(data, name, ["기준일", "자치구", "시설명"])
    if data.empty:
        raise ServiceError(f"{name}에 시설이 없어.", 500)
    if not data["기준일"].eq(date).all():
        raise ServiceError(f"{name}의 기준일이 모두 {date}이어야 해.", 500)
    if data[["자치구", "시설명"]].isna().any().any():
        raise ServiceError(f"{name}에 자치구나 시설명이 빈 행이 있어.", 500)
    return len(data)


def _project(row: pd.Series, name: str, zones_2025: int, zones_2026: int) -> BudgetProject:
    amount_2025, amount_2026 = int(row["2025예산_천원"]), int(row["2026예산_천원"])
    return BudgetProject(
        name=name,
        budget_2025=amount_2025,
        budget_2026=amount_2026,
        zones_2025=zones_2025,
        zones_2026=zones_2026,
        per_zone_2025_man_won=_man_won(amount_2025, zones_2025),
        per_zone_2026_man_won=_man_won(amount_2026, zones_2026),
    )


def zone_budget(data_dir: Path | str | None = None) -> ZoneBudget:
    budget = read_csv(BUDGET_FILE, data_dir)
    require_columns(budget, BUDGET_FILE, COLUMNS)
    child, elderly = _project_row(budget, CHILD_NAME), _project_row(budget, ELDERLY_NAME)
    if child["PDF쪽"] != elderly["PDF쪽"]:
        raise ServiceError("어린이와 노인·장애인 사업이 서로 다른 쪽에 있어.", 500)

    master = read_csv(PROTECTION_MASTER_FILE, data_dir)
    require_columns(master, PROTECTION_MASTER_FILE, ["시설ID", f"명단{ELDERLY_ZONE_YEAR}"])
    elderly_zones = int(master.loc[master[f"명단{ELDERLY_ZONE_YEAR}"].eq(1), "시설ID"].nunique())
    if elderly_zones == 0:
        raise ServiceError(f"{PROTECTION_MASTER_FILE}에 {ELDERLY_ZONE_YEAR}년 명단이 없어.", 500)

    return ZoneBudget(
        pdf_page=int(child["PDF쪽"]),
        child=_project(child, str(child["항목"]), _child_zones(data_dir, "2025-12-31"), _child_zones(data_dir, "2026-06-30")),
        elderly_disabled=_project(elderly, " ".join(str(elderly["항목"]).split()), elderly_zones, elderly_zones),
    )

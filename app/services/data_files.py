"""data 폴더의 정제 CSV를 읽는 공통 함수."""

from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.errors import ServiceError

OECD_FILE = "13_OECD_고령지표_wide.csv"
PANEL_FILE = "01_자치구연도_패널.csv"
PROTECTION_BOUNDARY_FILE = "05_보호구역_경계.csv"
SCHOOL_ZONE_FILE = "09_어린이보호구역_서울.csv"
HOTSPOT_FILE = "03_다발지역_서울.csv"
HOTSPOT_LINK_FILE = "06_다발지역_보호구역_연결.csv"
PROTECTION_MASTER_FILE = "04_보호구역_마스터.csv"
SEOUL_POPULATION_FILE = "11_서울_연령별_주민등록인구_202609.csv"
CHILD_ZONE_FILE = "12_경찰청_어린이보호구역_지정현황_20260630.csv"
CHILD_SUMMARY_FILE = "10_어린이보호구역_교통안전_요약.csv"
ACCIDENT_TREND_FILE = "15_TAAS_시도시군구_교통사고_2020-2025.csv"
NATIONAL_DEATHS_FILE = "17_전국사망자_막대도넛.csv"
ELDERLY_POPULATION_FILE = "18_전국_65세이상_주민등록인구.csv"
BOUNDARY_FILE = "08_서울_자치구_경계.geojson"


def resolve_data_dir(data_dir: Path | str | None = None) -> Path:
    return Path(data_dir) if data_dir else get_settings().data_dir


def read_csv(name: str, data_dir: Path | str | None = None) -> pd.DataFrame:
    path = resolve_data_dir(data_dir) / name
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except (OSError, ValueError) as error:
        raise ServiceError(f"{name} 파일을 읽지 못했어.", 500) from error


def require_columns(frame: pd.DataFrame, name: str, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ServiceError(f"{name}에 필요한 열이 없어: {', '.join(missing)}", 500)

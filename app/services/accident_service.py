"""서울·전국 교통사고, 고령·어린이 보행사고 통계."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import (
    AccidentTrend,
    ChildPedestrian,
    ElderlyPedestrian,
)
from app.services.data_files import (
    ACCIDENT_TREND_FILE,
    CHILD_SUMMARY_FILE,
    PANEL_FILE,
    read_csv,
    require_columns,
)

TREND_COLUMNS = [
    "year",
    "nationwide_accidents",
    "seoul_accidents",
    "seoul_injuries",
    "seoul_deaths",
]


def accident_trend(data_dir: Path | str | None = None) -> AccidentTrend:
    data = read_csv(ACCIDENT_TREND_FILE, data_dir)
    require_columns(data, ACCIDENT_TREND_FILE, TREND_COLUMNS)
    if data[TREND_COLUMNS].isna().any().any():
        raise ServiceError(f"{ACCIDENT_TREND_FILE}에 비어 있는 값이 있어.", 500)
    data = data.sort_values("year")
    return AccidentTrend(years=data[TREND_COLUMNS].to_dict(orient="records"))


def child_pedestrian(
    data_dir: Path | str | None = None, year: int = 2025
) -> ChildPedestrian:
    """보행자 교통사고 · 서울 · 12세 이하 행 한 개에서 사고·사망을 읽는다."""

    data = read_csv(CHILD_SUMMARY_FILE, data_dir)
    require_columns(
        data,
        CHILD_SUMMARY_FILE,
        ["자료구분", "지역", "사고연도", "연령범위", "사고건수", "사망자수"],
    )
    rows = data[
        data["자료구분"].eq("보행자 교통사고")
        & data["지역"].eq("서울")
        & data["사고연도"].eq(year)
        & data["연령범위"].eq("12세 이하")
    ]
    if len(rows) != 1:
        raise ServiceError(
            f"{year}년 서울 어린이 보행사고 행이 정확히 하나여야 하는데 {len(rows)}개야.",
            500,
        )

    row = rows.iloc[0]
    if pd.isna(row["사고건수"]) or pd.isna(row["사망자수"]):
        raise ServiceError(f"{year}년 서울 어린이 보행사고 값이 비어 있어.", 500)
    return ChildPedestrian(
        year=year, accidents=int(row["사고건수"]), deaths=int(row["사망자수"])
    )


ELDERLY_COLUMNS = {
    "accidents": "고령보행자_사고건수",
    "deaths": "고령보행자_사망자수",
    "injuries": "고령보행자_부상자수",
}


def elderly_pedestrian(
    data_dir: Path | str | None = None, year: int = 2025
) -> ElderlyPedestrian:
    """자치구 패널에서 서울 25개 자치구의 고령 보행자 사고를 합산한다."""

    try:
        data = read_csv(PANEL_FILE, data_dir)
        data_year = data[data["사고연도"] == year]

        if data_year["자치구명"].nunique() != 25:
            raise ServiceError(f"{year}년 서울 25개 자치구 자료를 확인할 수 없어.", 500)
        if data_year[list(ELDERLY_COLUMNS.values())].isna().any().any():
            raise ServiceError("사고 통계에 누락된 값이 있어.", 500)

        totals = {
            key: int(data_year[column].sum())
            for key, column in ELDERLY_COLUMNS.items()
        }
    except KeyError as error:
        raise ServiceError(str(error), 500) from error

    return ElderlyPedestrian(year=year, region="서울", districts=25, **totals)

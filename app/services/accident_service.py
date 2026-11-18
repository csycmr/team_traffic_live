"""서울·전국 교통사고, 고령·어린이 보행사고 통계."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import (
    AccidentTrend,
    ChildPedestrian,
    DistrictRate,
    DistrictRates,
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
    "population_65plus": "고령인구",
    "all_pedestrian_deaths": "전체보행자_사망자수",
}


def _elderly_totals(data: pd.DataFrame, year: int) -> dict:
    data_year = data[data["사고연도"] == year]

    if data_year["자치구명"].nunique() != 25:
        raise ServiceError(f"{year}년 서울 25개 자치구 자료를 확인할 수 없어.", 500)
    if data_year[list(ELDERLY_COLUMNS.values())].isna().any().any():
        raise ServiceError(f"{year}년 사고 통계에 누락된 값이 있어.", 500)

    return {
        key: int(data_year[column].sum()) for key, column in ELDERLY_COLUMNS.items()
    }


def elderly_pedestrian(
    data_dir: Path | str | None = None, year: int = 2025
) -> ElderlyPedestrian:
    """자치구 패널에서 서울 25개 자치구의 고령 보행자 사고를 합산한다."""

    try:
        data = read_csv(PANEL_FILE, data_dir)
        current = _elderly_totals(data, year)
        previous = _elderly_totals(data, year - 1)
    except KeyError as error:
        raise ServiceError(str(error), 500) from error

    return ElderlyPedestrian(
        year=year,
        region="서울",
        districts=25,
        **current,
        accidents_per_10k=round(
            current["accidents"] / current["population_65plus"] * 10000, 2
        ),
        death_share_percent=round(
            current["deaths"] / current["all_pedestrian_deaths"] * 100, 1
        ),
        previous_year=year - 1,
        accidents_change=current["accidents"] - previous["accidents"],
        deaths_change=current["deaths"] - previous["deaths"],
    )


DISTRICT_AXIS_MAX = 25  # 자치구 막대 축의 최댓값(1만 명당 건)
DISTRICT_COLUMNS = [
    "자치구명",
    "고령인구",
    "고령보행자_사고건수",
    "다발지역_수",
    "보호구역_명단시설수",
    "다발지역_보호구역중첩수",
]


def _district_year(data: pd.DataFrame, year: int) -> pd.DataFrame:
    frame = data[data["사고연도"] == year]
    if frame["자치구명"].nunique() != 25 or len(frame) != 25:
        raise ServiceError(f"{year}년 서울 25개 자치구 자료를 확인할 수 없어.", 500)
    if frame[DISTRICT_COLUMNS].isna().any().any():
        raise ServiceError(f"{year}년 자치구 자료에 누락된 값이 있어.", 500)
    return frame.set_index("자치구명")


def _ranks(rates: pd.Series) -> pd.Series:
    """화면에 보이는 소수 둘째 자리 사고율 기준 순위. 같은 값은 같은 순위."""
    return rates.round(2).rank(ascending=False, method="min").astype(int)


def elderly_district_rates(
    data_dir: Path | str | None = None, year: int = 2025
) -> DistrictRates:
    """자치구별 고령인구 1만 명당 고령 보행자 사고율, 순위와 전년 대비 변화."""

    data = read_csv(PANEL_FILE, data_dir)
    require_columns(data, PANEL_FILE, ["사고연도", *DISTRICT_COLUMNS])
    current = _district_year(data, year)
    previous = _district_year(data, year - 1)
    if set(current.index) != set(previous.index):
        raise ServiceError("전년과 올해의 자치구 목록이 달라.", 500)
    previous = previous.loc[current.index]

    rate = current["고령보행자_사고건수"] / current["고령인구"] * 10000
    previous_rate = previous["고령보행자_사고건수"] / previous["고령인구"] * 10000
    rank, previous_rank = _ranks(rate), _ranks(previous_rate)
    seoul_rate = round(
        current["고령보행자_사고건수"].sum() / current["고령인구"].sum() * 10000, 2
    )

    districts = []
    for name in rate.sort_values(ascending=False, kind="stable").index:
        accidents = int(current.at[name, "고령보행자_사고건수"])
        change = accidents - int(previous.at[name, "고령보행자_사고건수"])
        before = int(previous.at[name, "고령보행자_사고건수"])
        districts.append(
            DistrictRate(
                district=name,
                population_65plus=int(current.at[name, "고령인구"]),
                accidents=accidents,
                hotspots=int(current.at[name, "다발지역_수"]),
                protection_zones=int(current.at[name, "보호구역_명단시설수"]),
                overlaps=int(current.at[name, "다발지역_보호구역중첩수"]),
                accidents_per_10k=round(float(rate[name]), 2),
                bar_percent=round(float(rate[name]) / DISTRICT_AXIS_MAX * 100, 2),
                rank=int(rank[name]),
                previous_rank=int(previous_rank[name]),
                rank_change=int(previous_rank[name] - rank[name]),
                rate_gap=round(float(rate[name]) - seoul_rate, 2),
                accidents_change=change,
                accidents_change_percent=(
                    round(change / before * 100, 1) if before else None
                ),
            )
        )

    return DistrictRates(
        year=year,
        previous_year=year - 1,
        seoul_accidents_per_10k=seoul_rate,
        districts=districts,
    )

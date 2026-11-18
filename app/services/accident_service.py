"""서울·전국 교통사고, 고령·어린이 보행사고 통계."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import (
    AccidentTrend,
    NationalDeaths,
    CameraPeriod,
    ChildCameraEffect,
    ChildPedestrian,
    DistrictRate,
    DistrictRates,
    ElderlyPedestrian,
)
from app.services.data_files import (
    ACCIDENT_TREND_FILE,
    NATIONAL_DEATHS_FILE,
    CHILD_CAMERA_FILE,
    CHILD_SUMMARY_FILE,
    PANEL_FILE,
    read_csv,
    require_columns,
)

TAAS_COLUMNS = ["연도", "시도", "시군구", "사고건수", "사망자수", "부상자수"]


def _total_rows(data: pd.DataFrame, region: str) -> pd.DataFrame:
    """시군구가 '합계'인 행에서 한 시도(또는 전국 '합계')의 연도별 값을 고른다."""

    rows = data[data["시도"].eq(region) & data["시군구"].eq("합계")]
    if rows["연도"].duplicated().any():
        raise ServiceError(f"{ACCIDENT_TREND_FILE}에 {region} 합계 행이 연도마다 하나가 아니야.", 500)
    return rows.set_index("연도")


def accident_trend(data_dir: Path | str | None = None) -> AccidentTrend:
    """TAAS 시도·시군구 CSV의 전국 합계 행과 서울 합계 행으로 연도별 추이를 만든다."""

    data = read_csv(ACCIDENT_TREND_FILE, data_dir)
    require_columns(data, ACCIDENT_TREND_FILE, TAAS_COLUMNS)
    nationwide = _total_rows(data, "합계")
    seoul = _total_rows(data, "서울")
    years = sorted(set(nationwide.index) & set(seoul.index))
    if not years:
        raise ServiceError(f"{ACCIDENT_TREND_FILE}에서 전국·서울 합계 행을 찾지 못했어.", 500)

    values = ["사고건수", "사망자수", "부상자수"]
    if nationwide.loc[years, values].isna().any().any() or seoul.loc[years, values].isna().any().any():
        raise ServiceError(f"{ACCIDENT_TREND_FILE}에 비어 있는 값이 있어.", 500)

    return AccidentTrend(
        years=[
            {
                "year": int(year),
                "nationwide_accidents": int(nationwide.at[year, "사고건수"]),
                "nationwide_deaths": int(nationwide.at[year, "사망자수"]),
                "seoul_accidents": int(seoul.at[year, "사고건수"]),
                "seoul_injuries": int(seoul.at[year, "부상자수"]),
                "seoul_deaths": int(seoul.at[year, "사망자수"]),
            }
            for year in years
        ]
    )


NATIONAL_COLUMNS = {
    "total": "전체_사망자수",
    "elderly": "65세이상_사망자수",
    "share": "65세이상_비중(%)",
}
MODE_COLUMNS = {
    "pedestrian": "65세이상_보행중",
    "two_wheeler": "65세이상_이륜차",
    "car": "65세이상_승용차",
    "bicycle": "65세이상_자전거",
    "other": "65세이상_그외(차감)",
}


def national_deaths(data_dir: Path | str | None = None) -> NationalDeaths:
    """17번 CSV(막대·도넛 통합)에서 전국 연도별 사망자와 65세 이상 비중을 읽는다.

    전체 사망자는 TAAS 추이와, 비중과 '그 외'는 사망자 수에서 다시 계산한 값과 맞춰 본다.
    상태별 구분은 일부 칸만 비어 있으면 자료 오류로 보고, 전부 비어 있으면 null로 둔다.
    """

    data = read_csv(NATIONAL_DEATHS_FILE, data_dir)
    require_columns(
        data,
        NATIONAL_DEATHS_FILE,
        ["연도", *NATIONAL_COLUMNS.values(), *MODE_COLUMNS.values()],
    )
    taas = {row.year: row.nationwide_deaths for row in accident_trend(data_dir).years}

    years = []
    for _, row in data.sort_values("연도").iterrows():
        year = int(row["연도"])
        if row[list(NATIONAL_COLUMNS.values())].isna().any():
            raise ServiceError(f"{year}년 전국 사망자 값에 빈 칸이 있어.", 500)
        total, elderly = int(row["전체_사망자수"]), int(row["65세이상_사망자수"])
        if total != taas.get(year):
            raise ServiceError(
                f"{year}년 전체 사망자가 TAAS({taas.get(year)})와 {NATIONAL_DEATHS_FILE}({total})에서 달라.",
                500,
            )
        share = round(elderly / total * 100, 1)
        if abs(share - float(row["65세이상_비중(%)"])) > 0.05:
            raise ServiceError(f"{year}년 65세 이상 비중이 사망자 수와 맞지 않아.", 500)

        modes = row[list(MODE_COLUMNS.values())]
        by_mode = None
        if modes.notna().all():
            by_mode = {key: int(row[column]) for key, column in MODE_COLUMNS.items()}
            if sum(by_mode.values()) != elderly:
                raise ServiceError(f"{year}년 65세 이상 상태별 합이 사망자 수와 달라.", 500)
        elif modes.notna().any():
            raise ServiceError(f"{year}년 65세 이상 상태별 값이 일부만 비어 있어.", 500)

        years.append(
            {
                "year": year,
                "total_deaths": total,
                "elderly_deaths": elderly,
                "elderly_share_percent": share,
                "elderly_by_mode": by_mode,
            }
        )
    return NationalDeaths(years=years)


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


def child_camera_effect(data_dir: Path | str | None = None) -> ChildCameraEffect:
    """서울 무인단속카메라 설치 전·후 각 2년의 어린이 보행사고."""

    data = read_csv(CHILD_CAMERA_FILE, data_dir)
    columns = ["구분", "기간", "어린이_보행사고", "어린이_보행부상자", "설치대수"]
    require_columns(data, CHILD_CAMERA_FILE, columns)
    if data[columns].isna().any().any():
        raise ServiceError(f"{CHILD_CAMERA_FILE}에 비어 있는 값이 있어.", 500)
    rows = {}
    for label in ("설치 전", "설치 후"):
        found = data[data["구분"].eq(label)]
        if len(found) != 1:
            raise ServiceError(f"{CHILD_CAMERA_FILE}에 '{label}' 행이 정확히 하나여야 해.", 500)
        rows[label] = found.iloc[0]
    before, after = rows["설치 전"], rows["설치 후"]
    if before["어린이_보행사고"] <= 0:
        raise ServiceError("설치 전 사고 건수가 0이라 감소율을 계산할 수 없어.", 500)

    def period(row):
        return CameraPeriod(
            period=str(row["기간"]),
            accidents=int(row["어린이_보행사고"]),
            injuries=int(row["어린이_보행부상자"]),
        )

    drop = (before["어린이_보행사고"] - after["어린이_보행사고"]) / before["어린이_보행사고"] * 100
    return ChildCameraEffect(
        cameras=int(before["설치대수"]),
        before=period(before),
        after=period(after),
        accidents_reduction_percent=int(drop + 0.5),
    )

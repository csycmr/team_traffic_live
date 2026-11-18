"""서울 전체와 비교 자치구의 연도별 고령 보행자 사고 추이."""

from pathlib import Path

from app.errors import ServiceError
from app.models import ComparisonPoint, ComparisonSeries, DistrictComparison
from app.services.data_files import PANEL_FILE, read_csv, require_columns

DEFAULT_DISTRICTS = ("동대문구", "도봉구")
PANEL_COLUMNS = ["사고연도", "자치구명", "고령인구", "고령보행자_사고건수"]
SEOUL_DISTRICT_COUNT = 25


def _point(year: int, population: int, accidents: int) -> ComparisonPoint:
    return ComparisonPoint(
        year=year,
        population_65plus=population,
        accidents=accidents,
        accidents_per_10k=round(accidents / population * 10000, 2),
    )


def district_comparison(
    data_dir: Path | str | None = None,
    districts: tuple[str, ...] = DEFAULT_DISTRICTS,
) -> DistrictComparison:
    """서울 25개 자치구 합계(서울 전체)와 비교 자치구의 사고 건수·1만 명당 사고율."""

    data = read_csv(PANEL_FILE, data_dir)
    require_columns(data, PANEL_FILE, PANEL_COLUMNS)
    if data.duplicated(["사고연도", "자치구명"]).any():
        raise ServiceError(f"{PANEL_FILE}에 같은 자치구·연도가 겹쳐 있어.", 500)
    if data[PANEL_COLUMNS].isna().any().any():
        raise ServiceError(f"{PANEL_FILE}에 비어 있는 값이 있어.", 500)

    years = sorted(int(y) for y in data["사고연도"].unique())
    seoul_points = []
    for year in years:
        rows = data[data["사고연도"] == year]
        if rows["자치구명"].nunique() != SEOUL_DISTRICT_COUNT:
            raise ServiceError(f"{year}년 서울 25개 자치구 자료를 확인할 수 없어.", 500)
        seoul_points.append(
            _point(year, int(rows["고령인구"].sum()), int(rows["고령보행자_사고건수"].sum()))
        )
    series = [ComparisonSeries(name="서울 전체", points=seoul_points)]

    for name in districts:
        rows = data[data["자치구명"] == name].set_index("사고연도")
        if sorted(int(y) for y in rows.index) != years:
            raise ServiceError(f"{name}의 연도별 자료가 {years[0]}~{years[-1]}년 전부 있지 않아.", 500)
        series.append(
            ComparisonSeries(
                name=name,
                points=[
                    _point(y, int(rows.at[y, "고령인구"]), int(rows.at[y, "고령보행자_사고건수"]))
                    for y in years
                ],
            )
        )
    return DistrictComparison(years=years, series=series)

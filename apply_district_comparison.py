"""동대문구·도봉구 4년 비교(15번 차트)를 서버에 추가한다. 한 번만 돌리면 되고, 다시 돌려도 안전해.

사용법(프로젝트 루트에서):
    .\\.venv\\Scripts\\python.exe apply_district_comparison.py
"""

from pathlib import Path

ROOT = Path.cwd()

SERVICE = '"""서울 전체와 비교 자치구의 연도별 고령 보행자 사고 추이."""\n\nfrom pathlib import Path\n\nfrom app.errors import ServiceError\nfrom app.models import ComparisonPoint, ComparisonSeries, DistrictComparison\nfrom app.services.data_files import PANEL_FILE, read_csv, require_columns\n\nDEFAULT_DISTRICTS = ("동대문구", "도봉구")\nPANEL_COLUMNS = ["사고연도", "자치구명", "고령인구", "고령보행자_사고건수"]\nSEOUL_DISTRICT_COUNT = 25\n\n\ndef _point(year: int, population: int, accidents: int) -> ComparisonPoint:\n    return ComparisonPoint(\n        year=year,\n        population_65plus=population,\n        accidents=accidents,\n        accidents_per_10k=round(accidents / population * 10000, 2),\n    )\n\n\ndef district_comparison(\n    data_dir: Path | str | None = None,\n    districts: tuple[str, ...] = DEFAULT_DISTRICTS,\n) -> DistrictComparison:\n    """서울 25개 자치구 합계(서울 전체)와 비교 자치구의 사고 건수·1만 명당 사고율."""\n\n    data = read_csv(PANEL_FILE, data_dir)\n    require_columns(data, PANEL_FILE, PANEL_COLUMNS)\n    if data.duplicated(["사고연도", "자치구명"]).any():\n        raise ServiceError(f"{PANEL_FILE}에 같은 자치구·연도가 겹쳐 있어.", 500)\n    if data[PANEL_COLUMNS].isna().any().any():\n        raise ServiceError(f"{PANEL_FILE}에 비어 있는 값이 있어.", 500)\n\n    years = sorted(int(y) for y in data["사고연도"].unique())\n    seoul_points = []\n    for year in years:\n        rows = data[data["사고연도"] == year]\n        if rows["자치구명"].nunique() != SEOUL_DISTRICT_COUNT:\n            raise ServiceError(f"{year}년 서울 25개 자치구 자료를 확인할 수 없어.", 500)\n        seoul_points.append(\n            _point(year, int(rows["고령인구"].sum()), int(rows["고령보행자_사고건수"].sum()))\n        )\n    series = [ComparisonSeries(name="서울 전체", points=seoul_points)]\n\n    for name in districts:\n        rows = data[data["자치구명"] == name].set_index("사고연도")\n        if sorted(int(y) for y in rows.index) != years:\n            raise ServiceError(f"{name}의 연도별 자료가 {years[0]}~{years[-1]}년 전부 있지 않아.", 500)\n        series.append(\n            ComparisonSeries(\n                name=name,\n                points=[\n                    _point(y, int(rows.at[y, "고령인구"]), int(rows.at[y, "고령보행자_사고건수"]))\n                    for y in years\n                ],\n            )\n        )\n    return DistrictComparison(years=years, series=series)\n'
TEST = 'import pytest\n\nfrom app.errors import ServiceError\nfrom app.services import comparison_service\nfrom app.services.data_files import PANEL_FILE\n\nHEADER = "사고연도,자치구명,고령인구,고령보행자_사고건수\\n"\n\n\ndef panel_text(rows_for_a=None, districts=25):\n    lines = []\n    for year in (2024, 2025):\n        for i in range(districts):\n            name = "가구" if i == 0 else f"구{i}"\n            lines.append(f"{year},{name},1000,{10 + i}")\n    return HEADER + "\\n".join(lines)\n\n\ndef test_series_start_with_seoul_total(write_csv):\n    data_dir = write_csv(PANEL_FILE, panel_text())\n    result = comparison_service.district_comparison(data_dir, districts=("가구",))\n    assert result.years == [2024, 2025]\n    seoul, gu = result.series\n    assert seoul.name == "서울 전체"\n    assert seoul.points[0].population_65plus == 25000\n    assert seoul.points[0].accidents == sum(10 + i for i in range(25))\n    assert gu.name == "가구"\n    assert (gu.points[0].accidents, gu.points[0].accidents_per_10k) == (10, 100.0)\n\n\ndef test_unknown_district_is_error(write_csv):\n    data_dir = write_csv(PANEL_FILE, panel_text())\n    with pytest.raises(ServiceError, match="전부 있지"):\n        comparison_service.district_comparison(data_dir, districts=("없는구",))\n\n\ndef test_not_25_districts_is_error(write_csv):\n    data_dir = write_csv(PANEL_FILE, panel_text(districts=24))\n    with pytest.raises(ServiceError, match="25개"):\n        comparison_service.district_comparison(data_dir, districts=("가구",))\n\n\ndef test_blank_value_is_error(write_csv):\n    text = panel_text().replace("2025,가구,1000,10", "2025,가구,1000,")\n    data_dir = write_csv(PANEL_FILE, text)\n    with pytest.raises(ServiceError, match="비어"):\n        comparison_service.district_comparison(data_dir, districts=("가구",))\n\n\ndef test_real_data_matches_page(real_data_dir):\n    result = comparison_service.district_comparison(real_data_dir)\n    got = {\n        s.name: [(p.year, p.population_65plus, p.accidents, p.accidents_per_10k) for p in s.points]\n        for s in result.series\n    }\n    assert [s.name for s in result.series] == ["서울 전체", "동대문구", "도봉구"]\n    assert got["서울 전체"] == [\n        (2022, 1667411, 1846, 11.07), (2023, 1743696, 1973, 11.32),\n        (2024, 1824895, 1963, 10.76), (2025, 1912751, 2060, 10.77),\n    ]\n    assert got["동대문구"] == [\n        (2022, 64468, 138, 21.41), (2023, 67030, 155, 23.12),\n        (2024, 69582, 130, 18.68), (2025, 72779, 132, 18.14),\n    ]\n    assert got["도봉구"] == [\n        (2022, 66998, 49, 7.31), (2023, 70436, 61, 8.66),\n        (2024, 74223, 61, 8.22), (2025, 78335, 38, 4.85),\n    ]\n'
ROUTE_TEST = '\n\ndef test_district_comparison_endpoint():\n    body = client.get("/api/statistics/elderly/district-comparison").json()\n    assert body["years"] == [2022, 2023, 2024, 2025]\n    assert [s["name"] for s in body["series"]] == ["서울 전체", "동대문구", "도봉구"]\n'
MODELS_ADD = 'class ComparisonPoint(BaseModel):\n    year: int\n    population_65plus: int = Field(gt=0)\n    accidents: int = Field(ge=0)\n    accidents_per_10k: float = Field(ge=0)\n\n\nclass ComparisonSeries(BaseModel):\n    name: str\n    points: list[ComparisonPoint]\n\n\nclass DistrictComparison(BaseModel):\n    years: list[int]\n    series: list[ComparisonSeries]  # 서울 전체가 맨 앞, 그다음 비교 자치구\n'


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path, old, new, marker):
    text = read(path)
    if marker in text:
        print(f"이미 적용됨: {path}")
        return
    if text.count(old) != 1:
        raise SystemExit(f"못 찾음({text.count(old)}곳): {path} 의 {old.strip()[:40]}")
    write(path, text.replace(old, new))
    print(f"수정: {path}")


def create(path, text):
    target = ROOT / path
    if target.exists():
        print(f"이미 있음(덮어쓰지 않음): {path}")
        return
    write(path, text)
    print(f"생성: {path}")


if not (ROOT / "app" / "main.py").exists():
    raise SystemExit("프로젝트 루트(app 폴더가 있는 곳)에서 실행해 줘.")

create("app/services/comparison_service.py", SERVICE)
create("tests/test_comparison_service.py", TEST)

models = read("app/models.py")
if "class DistrictComparison" in models:
    print("이미 적용됨: app/models.py")
else:
    write("app/models.py", models.rstrip() + "\n\n\n" + MODELS_ADD)
    print("수정: app/models.py")

replace_once("app/main.py", "    DistrictRates,\n", "    DistrictComparison,\n    DistrictRates,\n", "DistrictComparison,")
replace_once("app/main.py", "    citydata_service,\n", "    citydata_service,\n    comparison_service,\n", "comparison_service,")
replace_once(
    "app/main.py",
    '@app.get("/api/statistics/elderly-population"',
    '@app.get("/api/statistics/elderly/district-comparison", response_model=DistrictComparison)\n'
    "def get_district_comparison():\n"
    "    return comparison_service.district_comparison()\n\n\n"
    '@app.get("/api/statistics/elderly-population"',
    "district-comparison",
)

routes = read("tests/test_fastapi_routes.py")
if "test_district_comparison_endpoint" in routes:
    print("이미 적용됨: tests/test_fastapi_routes.py")
else:
    write("tests/test_fastapi_routes.py", routes.rstrip() + "\n" + ROUTE_TEST)
    print("수정: tests/test_fastapi_routes.py")

print("끝. python -m pytest -q 로 확인해 줘.")

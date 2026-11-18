"""사고다발지역 검토(16번 구간)를 서버에 추가한다. 한 번만 돌리면 되고, 다시 돌려도 안전해.

사용법(프로젝트 루트에서):
    .\\.venv\\Scripts\\python.exe apply_hotspots.py
"""

from pathlib import Path

ROOT = Path.cwd()

SERVICE = '"""사고다발지역과 노인보호구역 경계 중첩 자료."""\n\nimport math\nimport re\nfrom pathlib import Path\n\nimport pandas as pd\n\nfrom app.errors import ServiceError\nfrom app.models import (\n    Hotspot,\n    HotspotCandidate,\n    HotspotDistrictCount,\n    Hotspots,\n    HotspotReview,\n    HotspotReviewItem,\n)\nfrom app.services.data_files import (\n    HOTSPOT_FILE,\n    HOTSPOT_LINK_FILE,\n    PANEL_FILE,\n    read_csv,\n    require_columns,\n)\n\nCANDIDATE_DISTRICTS = ("동대문구", "중랑구", "은평구", "금천구")  # 화면의 현장 검토 후보 예시\nHOTSPOT_COLUMNS = [\n    "다발지역FID", "사고연도", "자치구코드", "자치구명", "법정동명", "부근명",\n    "지점명", "사고건수", "사망자수", "경도", "위도",\n]\nLINK_COLUMNS = ["다발지역FID", "사고연도", "최단거리_m", "경계중첩"]\n\n\ndef _hotspot_rows(data_dir, year: int) -> pd.DataFrame:\n    data = read_csv(HOTSPOT_FILE, data_dir)\n    require_columns(data, HOTSPOT_FILE, HOTSPOT_COLUMNS)\n    rows = data[data["사고연도"] == year]\n    if rows.empty:\n        raise ServiceError(f"{HOTSPOT_FILE}에 {year}년 사고다발지역이 없어.", 500)\n    if rows["다발지역FID"].duplicated().any():\n        raise ServiceError(f"{HOTSPOT_FILE}에 같은 다발지역FID가 겹쳐 있어.", 500)\n    if rows[HOTSPOT_COLUMNS].isna().any().any():\n        raise ServiceError(f"{HOTSPOT_FILE}의 {year}년 값에 비어 있는 칸이 있어.", 500)\n    return rows\n\n\ndef hotspots(data_dir: Path | str | None = None, year: int = 2025) -> Hotspots:\n    """지도에 점으로 찍을 사고다발지역. 자치구코드, 다발지역FID 순서."""\n\n    rows = _hotspot_rows(data_dir, year).sort_values(["자치구코드", "다발지역FID"])\n    return Hotspots(\n        year=year,\n        locations=[\n            Hotspot(\n                id=str(row.다발지역FID),\n                name=row.지점명.replace("서울특별시", "서울", 1),\n                district=row.자치구명,\n                crashes=int(row.사고건수),\n                deaths=int(row.사망자수),\n                lat=float(row.위도),\n                lng=float(row.경도),\n            )\n            for row in rows.itertuples()\n        ],\n    )\n\n\ndef _meters(value: float) -> int:\n    """0.5는 내려서 정수 m로 만든다. (335.5 → 335)"""\n\n    return int(math.ceil(value - 0.5))\n\n\nNEARBY_SUFFIX = re.compile(r"\\s*부근$")\n\n\ndef _label(row) -> str:\n    return " ".join([row.자치구명, row.법정동명, NEARBY_SUFFIX.sub("", str(row.부근명))])\n\n\ndef hotspot_review(\n    data_dir: Path | str | None = None,\n    year: int = 2025,\n    candidates: tuple[str, ...] = CANDIDATE_DISTRICTS,\n) -> HotspotReview:\n    """사고다발지역을 보호구역 경계와 비교한 목록·자치구별 막대·후보 표."""\n\n    spots = _hotspot_rows(data_dir, year)\n    links = read_csv(HOTSPOT_LINK_FILE, data_dir)\n    require_columns(links, HOTSPOT_LINK_FILE, LINK_COLUMNS)\n    links = links[links["사고연도"] == year]\n    if links["다발지역FID"].duplicated().any():\n        raise ServiceError(f"{HOTSPOT_LINK_FILE}에 같은 다발지역FID가 겹쳐 있어.", 500)\n\n    merged = spots.merge(links[["다발지역FID", "최단거리_m", "경계중첩"]], on="다발지역FID", how="left")\n    if len(merged) != len(spots):\n        raise ServiceError("다발지역과 보호구역 연결표의 행 수가 달라.", 500)\n\n    undetermined = merged["경계중첩"].isna()\n    judged = merged[~undetermined]\n    overlapping_mask = judged["경계중첩"].eq(1)\n    if not set(judged["경계중첩"].unique()) <= {0, 1}:\n        raise ServiceError(f"{HOTSPOT_LINK_FILE}의 경계중첩은 0 또는 1이어야 해.", 500)\n    if judged["최단거리_m"].isna().any():\n        raise ServiceError(f"{HOTSPOT_LINK_FILE}에 최단거리가 비어 있는 판정 행이 있어.", 500)\n\n    ordered = judged.sort_values(\n        ["사고건수", "최단거리_m", "자치구코드", "다발지역FID"],\n        ascending=[False, True, True, True],\n    )\n    items = [\n        HotspotReviewItem(\n            name=_label(row),\n            district=row.자치구명,\n            crashes=int(row.사고건수),\n            overlaps=bool(row.경계중첩 == 1),\n            distance_m=None if row.경계중첩 == 1 else _meters(float(row.최단거리_m)),\n        )\n        for row in ordered.itertuples()\n    ]\n\n    overlapping = int(overlapping_mask.sum())\n    outside = int((~overlapping_mask).sum())\n    total = overlapping + outside\n\n    per_district = (\n        merged.assign(\n            inside=merged["경계중첩"].eq(1).astype(int),\n            out=merged["경계중첩"].eq(0).astype(int),\n        )\n        .groupby(["자치구코드", "자치구명"], as_index=False)\n        .agg(inside=("inside", "sum"), out=("out", "sum"))\n    )\n    per_district["total"] = per_district["inside"] + per_district["out"]\n    per_district = per_district[per_district["total"] > 0].sort_values(\n        ["total", "inside", "자치구코드"], ascending=[False, False, True]\n    )\n    districts = [\n        HotspotDistrictCount(district=row.자치구명, overlapping=int(row.inside), outside=int(row.out))\n        for row in per_district.itertuples()\n    ]\n\n    panel = read_csv(PANEL_FILE, data_dir)\n    require_columns(panel, PANEL_FILE, ["사고연도", "자치구명", "고령인구", "고령보행자_사고건수"])\n    panel = panel[panel["사고연도"] == year].set_index("자치구명")\n    picked = []\n    for name in candidates:\n        mine = merged[merged["자치구명"] == name]\n        if mine.empty or name not in panel.index:\n            raise ServiceError(f"{name}의 {year}년 다발지역·사고 자료가 없어.", 500)\n        accidents = panel.at[name, "고령보행자_사고건수"]\n        population = panel.at[name, "고령인구"]\n        if pd.isna(accidents) or pd.isna(population) or population <= 0:\n            raise ServiceError(f"{name}의 {year}년 사고·인구 값이 비어 있어.", 500)\n        picked.append(\n            HotspotCandidate(\n                district=name,\n                selected=len(mine),\n                outside=int(mine["경계중첩"].eq(0).sum()),\n                overlapping=int(mine["경계중첩"].eq(1).sum()),\n                undetermined=int(mine["경계중첩"].isna().sum()),\n                accidents_per_10k=round(float(accidents / population * 10000), 2),\n            )\n        )\n\n    return HotspotReview(\n        year=year,\n        total=total,\n        overlapping=overlapping,\n        outside=outside,\n        undetermined=int(undetermined.sum()),\n        outside_percent=round(outside / total * 100, 1) if total else 0.0,\n        items=items,\n        districts=districts,\n        candidates=picked,\n    )\n'
TEST = 'import json\n\nimport pytest\n\nfrom app.errors import ServiceError\nfrom app.services import hotspot_service\nfrom app.services.data_files import HOTSPOT_FILE, HOTSPOT_LINK_FILE, PANEL_FILE\n\nHOTSPOT_HEADER = "다발지역FID,사고연도,자치구코드,자치구명,법정동명,부근명,지점명,사고건수,사망자수,경도,위도\\n"\nLINK_HEADER = "다발지역FID,사고연도,최단거리_m,경계중첩\\n"\nPANEL_HEADER = "자치구명,사고연도,고령인구,고령보행자_사고건수\\n"\n\n\ndef write_all(write_csv, spots, links, panel="가구,2025,1000,20\\n나구,2025,2000,10"):\n    data_dir = write_csv(HOTSPOT_FILE, HOTSPOT_HEADER + spots)\n    (data_dir / HOTSPOT_LINK_FILE).write_text(LINK_HEADER + links + "\\n", encoding="utf-8-sig")\n    (data_dir / PANEL_FILE).write_text(PANEL_HEADER + panel + "\\n", encoding="utf-8-sig")\n    return data_dir\n\n\nSPOTS = "\\n".join(\n    [\n        "1,2025,11110,가구,갑동,갑교차로 부근,서울특별시 가구 갑동(갑교차로 부근),5,1,127.0,37.5",\n        "2,2025,11110,가구,을동,을시장 부근,서울특별시 가구 을동(을시장 부근),5,0,127.1,37.6",\n        "3,2025,11140,나구,병동,병역 4호선 부근,서울특별시 나구 병동(병역 4호선 부근),3,0,127.2,37.7",\n        "4,2024,11140,나구,정동,정교차로 부근,서울특별시 나구 정동(정교차로 부근),9,0,127.3,37.8",\n    ]\n)\n\n\ndef test_hotspots_are_2025_only_and_sorted(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\\n2,2025,200.5,0\\n3,2025,50,0")\n    result = hotspot_service.hotspots(data_dir)\n    assert result.year == 2025\n    assert [h.id for h in result.locations] == ["1", "2", "3"]\n    first = result.locations[0]\n    assert first.name == "서울 가구 갑동(갑교차로 부근)"  # 서울특별시 → 서울\n    assert (first.crashes, first.deaths, first.lat, first.lng) == (5, 1, 37.5, 127.0)\n\n\ndef test_review_counts_order_and_distance(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\\n2,2025,200.5,0\\n3,2025,50,0")\n    review = hotspot_service.hotspot_review(data_dir, candidates=("가구", "나구"))\n    assert (review.total, review.overlapping, review.outside, review.undetermined) == (3, 1, 2, 0)\n    assert review.outside_percent == 66.7\n    # 사고 많은 순, 같으면 가까운 순(겹침은 0m)\n    assert [(i.name, i.overlaps, i.distance_m) for i in review.items] == [\n        ("가구 갑동 갑교차로", True, None),\n        ("가구 을동 을시장", False, 200),  # 200.5는 내린다\n        ("나구 병동 병역 4호선", False, 50),\n    ]\n    assert [(d.district, d.overlapping, d.outside) for d in review.districts] == [\n        ("가구", 1, 1),\n        ("나구", 0, 1),\n    ]\n    assert [(c.district, c.selected, c.outside, c.overlapping, c.undetermined, c.accidents_per_10k)\n            for c in review.candidates] == [("가구", 2, 1, 1, 0, 200.0), ("나구", 1, 1, 0, 0, 50.0)]\n\n\ndef test_unjudged_hotspot_counts_as_undetermined(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\\n2,2025,,\\n3,2025,50,0")\n    review = hotspot_service.hotspot_review(data_dir, candidates=("가구",))\n    assert (review.total, review.undetermined) == (2, 1)\n    assert review.candidates[0].selected == 2 and review.candidates[0].undetermined == 1\n\n\ndef test_missing_link_row_is_undetermined_not_error(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\\n3,2025,50,0")\n    review = hotspot_service.hotspot_review(data_dir, candidates=("가구",))\n    assert review.undetermined == 1\n\n\ndef test_unknown_candidate_is_error(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\\n2,2025,200,0\\n3,2025,50,0")\n    with pytest.raises(ServiceError, match="없어"):\n        hotspot_service.hotspot_review(data_dir, candidates=("없는구",))\n\n\ndef test_no_hotspots_for_year_is_error(write_csv):\n    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1")\n    with pytest.raises(ServiceError, match="없어"):\n        hotspot_service.hotspots(data_dir, year=2030)\n\n\ndef test_duplicate_fid_is_error(write_csv):\n    spots = SPOTS + "\\n1,2025,11110,가구,갑동,갑교차로 부근,서울특별시 가구 갑동(갑교차로 부근),5,1,127.0,37.5"\n    data_dir = write_all(write_csv, spots, "1,2025,0,1")\n    with pytest.raises(ServiceError, match="겹쳐"):\n        hotspot_service.hotspots(data_dir)\n\n\ndef test_real_locations_equal_json_file(real_data_dir):\n    expected = json.loads((real_data_dir / "accident-hotspots-2025.json").read_text(encoding="utf-8"))\n    assert hotspot_service.hotspots(real_data_dir).model_dump() == expected\n\n\ndef test_real_review_matches_page(real_data_dir):\n    review = hotspot_service.hotspot_review(real_data_dir)\n    assert (review.total, review.overlapping, review.outside, review.undetermined) == (71, 12, 59, 0)\n    assert review.outside_percent == 83.1\n    assert len(review.items) == 71 and len(review.districts) == 21\n    top = [(i.name, i.crashes, "겹침" if i.overlaps else f"{i.distance_m}m") for i in review.items[:12]]\n    assert top == [\n        ("동대문구 제기동 동서시장", 12, "겹침"),\n        ("동대문구 제기동 청량리전통시장", 10, "겹침"),\n        ("동작구 상도동 계령약국", 10, "111m"),\n        ("강북구 번동 수유역교차로", 7, "408m"),\n        ("동작구 사당동 남성사계시장", 7, "451m"),\n        ("성북구 길음동 길음역교차로", 7, "468m"),\n        ("성북구 종암동 종암동주민센터", 7, "856m"),\n        ("강북구 미아동 미아사거리역 4호선", 7, "1372m"),\n        ("성북구 상월곡동 장위2동주민센터", 6, "겹침"),\n        ("관악구 봉천동 낙성대역 2호선", 6, "겹침"),\n        ("강동구 명일동 굽은다리역교차로", 6, "겹침"),\n        ("동대문구 제기동 경동시장교차로", 6, "74m"),\n    ]\n    assert [(d.district, d.overlapping, d.outside) for d in review.districts[:6]] == [\n        ("동대문구", 3, 7), ("중랑구", 0, 7), ("성북구", 1, 4),\n        ("동작구", 1, 4), ("강동구", 1, 4), ("은평구", 0, 5),\n    ]\n    assert [(c.district, c.selected, c.outside, c.overlapping, c.undetermined, c.accidents_per_10k)\n            for c in review.candidates] == [\n        ("동대문구", 10, 7, 3, 0, 18.14), ("중랑구", 7, 7, 0, 0, 11.91),\n        ("은평구", 5, 5, 0, 0, 11.42), ("금천구", 4, 4, 0, 0, 16.38),\n    ]\n    assert any(i.distance_m == 335 for i in review.items)  # 335.5m는 내림\n'
ROUTE_TEST = '\n\ndef test_hotspot_endpoints():\n    spots = client.get("/api/statistics/hotspots").json()\n    assert spots["year"] == 2025 and len(spots["locations"]) == 71\n    review = client.get("/api/statistics/hotspots/review").json()\n    assert (review["total"], review["overlapping"], review["outside"]) == (71, 12, 59)\n'
MODELS_ADD = 'class Hotspot(BaseModel):\n    id: str\n    name: str\n    district: str\n    crashes: int = Field(ge=0)\n    deaths: int = Field(ge=0)\n    lat: float\n    lng: float\n\n\nclass Hotspots(BaseModel):\n    year: int\n    locations: list[Hotspot]\n\n\nclass HotspotReviewItem(BaseModel):\n    name: str  # 자치구 법정동 부근명\n    district: str\n    crashes: int = Field(ge=0)\n    overlaps: bool  # 보호구역 경계와 겹침\n    distance_m: int | None  # 겹치면 None, 아니면 가장 가까운 경계까지 직선거리\n\n\nclass HotspotDistrictCount(BaseModel):\n    district: str\n    overlapping: int = Field(ge=0)\n    outside: int = Field(ge=0)\n\n\nclass HotspotCandidate(BaseModel):\n    district: str\n    selected: int = Field(ge=0)  # 선정 영역 수\n    outside: int = Field(ge=0)\n    overlapping: int = Field(ge=0)\n    undetermined: int = Field(ge=0)\n    accidents_per_10k: float = Field(ge=0)\n\n\nclass HotspotReview(BaseModel):\n    year: int\n    total: int = Field(ge=0)  # 판정 가능한 다발지역\n    overlapping: int = Field(ge=0)\n    outside: int = Field(ge=0)\n    undetermined: int = Field(ge=0)\n    outside_percent: float\n    items: list[HotspotReviewItem]  # 사고 많은 순\n    districts: list[HotspotDistrictCount]\n    candidates: list[HotspotCandidate]\n'
ROUTE_CODE = '@app.get("/api/statistics/hotspots", response_model=Hotspots)\ndef get_hotspots():\n    return hotspot_service.hotspots()\n\n\n@app.get("/api/statistics/hotspots/review", response_model=HotspotReview)\ndef get_hotspot_review():\n    return hotspot_service.hotspot_review()\n\n\n'


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

create("app/services/hotspot_service.py", SERVICE)
create("tests/test_hotspot_service.py", TEST)

replace_once(
    "app/services/data_files.py",
    'PANEL_FILE = "01_자치구연도_패널.csv"\n',
    'PANEL_FILE = "01_자치구연도_패널.csv"\n'
    'HOTSPOT_FILE = "03_다발지역_서울.csv"\n'
    'HOTSPOT_LINK_FILE = "06_다발지역_보호구역_연결.csv"\n',
    "HOTSPOT_FILE",
)

models = read("app/models.py")
if "class HotspotReview" in models:
    print("이미 적용됨: app/models.py")
else:
    write("app/models.py", models.rstrip() + "\n\n\n" + MODELS_ADD)
    print("수정: app/models.py")

replace_once("app/main.py", "    ElderlyPopulation,\n", "    ElderlyPopulation,\n    HotspotReview,\n    Hotspots,\n", "    HotspotReview,")
replace_once("app/main.py", "    citydata_service,\n", "    citydata_service,\n    hotspot_service,\n", "    hotspot_service,")
replace_once(
    "app/main.py",
    '@app.get("/api/statistics/elderly-population"',
    ROUTE_CODE + '@app.get("/api/statistics/elderly-population"',
    "/api/statistics/hotspots",
)

routes = read("tests/test_fastapi_routes.py")
if "test_hotspot_endpoints" in routes:
    print("이미 적용됨: tests/test_fastapi_routes.py")
else:
    write("tests/test_fastapi_routes.py", routes.rstrip() + "\n" + ROUTE_TEST)
    print("수정: tests/test_fastapi_routes.py")

print("끝. python -m pytest -q 로 확인해 줘.")

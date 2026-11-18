"""서울시 보호구역 개선 예산(18번 화면) 서버 코드를 추가하거나 최신판으로 바꾼다. 다시 돌려도 안전해.
(예전 버전을 이미 돌렸어도 이걸 한 번 더 돌리면 돼.)

어린이 지정 구역 수는 data 폴더의 아래 두 CSV 행 수에서 가져와:
    21_서울_어린이보호구역_지정현황_20251231_목록용.csv  (2025년 예산용)
    22_서울_어린이보호구역_지정현황_20260630_목록용.csv  (2026년 예산용)
이 CSV는 make_child_zone_list.py로 엑셀에서 만들 수 있어.

사용법(프로젝트 루트에서):
    .\\.venv\\Scripts\\python.exe apply_zone_budget.py
"""

from pathlib import Path

ROOT = Path.cwd()

SERVICE = '"""서울시 2026년 예산서의 보호구역 개선 세부사업 편성액."""\n\nfrom pathlib import Path\n\nimport pandas as pd\n\nfrom app.errors import ServiceError\nfrom app.models import BudgetProject, ZoneBudget\nfrom app.services.data_files import (\n    BUDGET_FILE,\n    CHILD_LIST_FILES,\n    PROTECTION_MASTER_FILE,\n    read_csv,\n    require_columns,\n)\n\nCOLUMNS = ["PDF쪽", "구분", "행유형", "항목", "2025예산_천원", "2026예산_천원"]\nCHILD_NAME = "어린이보호구역개선(전환사업)"\nELDERLY_NAME = "노인·장애인보호구역개선(전환사업)"\nELDERLY_ZONE_YEAR = 2025\n\n\ndef _project_row(budget: pd.DataFrame, name: str) -> pd.Series:\n    """공백을 뺀 항목명이 같은 세출예산 \'연도별 예산 비교\' 행은 정확히 하나여야 한다."""\n\n    key = budget["항목"].astype(str).str.replace(r"\\s+", "", regex=True)\n    rows = budget[budget["구분"].eq("세출예산") & budget["행유형"].eq("연도별 예산 비교") & key.eq(name)]\n    if len(rows) != 1:\n        raise ServiceError(f"{BUDGET_FILE}에서 \'{name}\' 행이 정확히 하나여야 하는데 {len(rows)}개야.", 500)\n    row = rows.iloc[0]\n    if pd.isna(row["2025예산_천원"]) or pd.isna(row["2026예산_천원"]):\n        raise ServiceError(f"{BUDGET_FILE}의 \'{name}\' 예산 값이 비어 있어.", 500)\n    return row\n\n\ndef _man_won(thousand_won: int, zones: int) -> int:\n    """천원 단위 예산을 구역 수로 나눠 만 원 단위로 반올림한다."""\n\n    return int(thousand_won * 1000 / zones / 10000 + 0.5)\n\n\ndef _child_zones(data_dir, date: str) -> int:\n    """연말 기준일의 서울 어린이보호구역 지정 목록 행 수(시설 한 곳이 한 줄)."""\n\n    name = CHILD_LIST_FILES.get(date)\n    if name is None:\n        raise ServiceError(f"{date} 어린이보호구역 지정 목록 파일이 설정에 없어.", 500)\n    data = read_csv(name, data_dir)\n    require_columns(data, name, ["기준일", "자치구", "시설명"])\n    if data.empty:\n        raise ServiceError(f"{name}에 시설이 없어.", 500)\n    if not data["기준일"].eq(date).all():\n        raise ServiceError(f"{name}의 기준일이 모두 {date}이어야 해.", 500)\n    if data[["자치구", "시설명"]].isna().any().any():\n        raise ServiceError(f"{name}에 자치구나 시설명이 빈 행이 있어.", 500)\n    return len(data)\n\n\ndef _project(row: pd.Series, name: str, zones_2025: int, zones_2026: int) -> BudgetProject:\n    amount_2025, amount_2026 = int(row["2025예산_천원"]), int(row["2026예산_천원"])\n    return BudgetProject(\n        name=name,\n        budget_2025=amount_2025,\n        budget_2026=amount_2026,\n        zones_2025=zones_2025,\n        zones_2026=zones_2026,\n        per_zone_2025_man_won=_man_won(amount_2025, zones_2025),\n        per_zone_2026_man_won=_man_won(amount_2026, zones_2026),\n    )\n\n\ndef zone_budget(data_dir: Path | str | None = None) -> ZoneBudget:\n    budget = read_csv(BUDGET_FILE, data_dir)\n    require_columns(budget, BUDGET_FILE, COLUMNS)\n    child, elderly = _project_row(budget, CHILD_NAME), _project_row(budget, ELDERLY_NAME)\n    if child["PDF쪽"] != elderly["PDF쪽"]:\n        raise ServiceError("어린이와 노인·장애인 사업이 서로 다른 쪽에 있어.", 500)\n\n    master = read_csv(PROTECTION_MASTER_FILE, data_dir)\n    require_columns(master, PROTECTION_MASTER_FILE, ["시설ID", f"명단{ELDERLY_ZONE_YEAR}"])\n    elderly_zones = int(master.loc[master[f"명단{ELDERLY_ZONE_YEAR}"].eq(1), "시설ID"].nunique())\n    if elderly_zones == 0:\n        raise ServiceError(f"{PROTECTION_MASTER_FILE}에 {ELDERLY_ZONE_YEAR}년 명단이 없어.", 500)\n\n    return ZoneBudget(\n        pdf_page=int(child["PDF쪽"]),\n        child=_project(child, str(child["항목"]), _child_zones(data_dir, "2025-12-31"), _child_zones(data_dir, "2026-06-30")),\n        elderly_disabled=_project(elderly, " ".join(str(elderly["항목"]).split()), elderly_zones, elderly_zones),\n    )\n'

TEST = 'import pytest\n\nfrom app.errors import ServiceError\nfrom app.services import budget_service\nfrom app.services.data_files import BUDGET_FILE, CHILD_LIST_FILES, PROTECTION_MASTER_FILE\n\nHEADER = "PDF쪽,구분,행유형,항목,2025예산_천원,2026예산_천원\\n"\n\n\ndef write_list(tmp_path, date, count, written_date=None):\n    lines = "".join(f"{written_date or date},가구,시설{i}\\n" for i in range(count))\n    (tmp_path / CHILD_LIST_FILES[date]).write_text("기준일,자치구,시설명\\n" + lines, encoding="utf-8-sig")\n\n\ndef write(tmp_path, rows):\n    (tmp_path / BUDGET_FILE).write_text(HEADER + rows, encoding="utf-8-sig")\n    (tmp_path / PROTECTION_MASTER_FILE).write_text("시설ID,명단2025\\nZ1,1\\nZ1,1\\nZ2,1\\nZ3,0\\n", encoding="utf-8-sig")\n    write_list(tmp_path, "2025-12-31", 50)\n    write_list(tmp_path, "2026-06-30", 40)\n    return tmp_path\n\n\nROWS = (\n    \'616,세출예산,연도별 예산 비교,어린이 보호구역 개선(전환사업),1000,500\\n\'\n    \'616,세출예산,연도별 예산 비교,"노인· 장애인 보호구역 개선(전환사업)",300,100\\n\'\n    \'1850,명시이월 사업조서,원문,어린이 보호구역 개선(전환사업),,\\n\'\n)\n\n\ndef test_rows_are_found_ignoring_spaces_and_other_sections(tmp_path):\n    result = budget_service.zone_budget(write(tmp_path, ROWS))\n    assert (result.pdf_page, result.child.budget_2025, result.child.budget_2026) == (616, 1000, 500)\n    assert result.elderly_disabled.name == "노인· 장애인 보호구역 개선(전환사업)"\n    assert result.elderly_disabled.zones_2025 == 2  # 같은 시설ID는 한 곳\n    assert (result.elderly_disabled.per_zone_2025_man_won, result.elderly_disabled.per_zone_2026_man_won) == (15, 5)\n    assert (result.child.zones_2025, result.child.zones_2026) == (50, 40)\n    assert (result.child.per_zone_2025_man_won, result.child.per_zone_2026_man_won) == (2, 1)  # 1.0e6/50 원=2만, 0.5e6/40 원=1.25만\n\n\ndef test_missing_project_is_error(tmp_path):\n    with pytest.raises(ServiceError, match="정확히 하나"):\n        budget_service.zone_budget(write(tmp_path, ROWS.split("\\n")[0] + "\\n"))\n\n\ndef test_list_with_other_date_is_error(tmp_path):\n    data_dir = write(tmp_path, ROWS)\n    write_list(data_dir, "2025-12-31", 50, written_date="2026-06-30")\n    with pytest.raises(ServiceError, match="기준일"):\n        budget_service.zone_budget(data_dir)\n\n\ndef test_missing_list_file_is_error(tmp_path):\n    data_dir = write(tmp_path, ROWS)\n    (data_dir / CHILD_LIST_FILES["2026-06-30"]).unlink()\n    with pytest.raises(ServiceError, match="읽지 못했어|없어"):\n        budget_service.zone_budget(data_dir)\n\n\ndef test_duplicate_project_is_error(tmp_path):\n    dup = \'616,세출예산,연도별 예산 비교,어린이 보호구역 개선(전환사업),1,1\\n\'\n    with pytest.raises(ServiceError, match="정확히 하나"):\n        budget_service.zone_budget(write(tmp_path, ROWS + dup))\n\n\ndef test_real_data_matches_page(real_data_dir):\n    result = budget_service.zone_budget(real_data_dir)\n    assert result.pdf_page == 616\n    # 화면: 237.23억 / 182.71억 / 18.64억 / 10.63억\n    assert [round(v / 100000, 2) for v in (\n        result.child.budget_2025, result.child.budget_2026,\n        result.elderly_disabled.budget_2025, result.elderly_disabled.budget_2026)] == [237.23, 182.71, 18.64, 10.63]\n    assert (result.child.zones_2025, result.child.zones_2026) == (1658, 1630)\n    assert (result.child.per_zone_2025_man_won, result.child.per_zone_2026_man_won) == (1431, 1121)\n    assert result.elderly_disabled.zones_2025 == result.elderly_disabled.zones_2026 == 195\n    assert (result.elderly_disabled.per_zone_2025_man_won, result.elderly_disabled.per_zone_2026_man_won) == (956, 545)\n'

ROUTE_TEST = '\n\ndef test_zone_budget_endpoint():\n    body = client.get("/api/budget/zone-improvement").json()\n    assert body["pdf_page"] == 616 and body["elderly_disabled"]["zones_2025"] == 195 and body["child"]["zones_2026"] == 1630\n'
MODELS_ADD = 'class BudgetProject(BaseModel):\n    name: str  # 예산서 세부사업명\n    budget_2025: int = Field(ge=0)  # 천원\n    budget_2026: int = Field(ge=0)\n    zones_2025: int = Field(gt=0)  # 2025년 예산 편성 기준(2024년 12월 말) 지정 구역 수\n    zones_2026: int = Field(gt=0)  # 2026년 예산 편성 기준(2025년 12월 말) 지정 구역 수\n    per_zone_2025_man_won: int = Field(ge=0)  # 1곳당 환산액(만 원)\n    per_zone_2026_man_won: int = Field(ge=0)\n\n\nclass ZoneBudget(BaseModel):\n    pdf_page: int\n    child: BudgetProject\n    elderly_disabled: BudgetProject  # 장애인 보호구역과 합산 편성이라 1곳당 금액은 상한 추정치\n'
ROUTE_CODE = '@app.get("/api/budget/zone-improvement", response_model=ZoneBudget)\ndef get_zone_budget():\n    return budget_service.zone_budget()\n\n\n'
LIST_BLOCK = '# 기준일별 서울 어린이보호구역 지정 목록(시설 한 곳이 한 줄). 예산 표의 구역 수에 쓴다.\n# 2025년 예산 = 2025-12-31 기준, 2026년 예산 = 2026-06-30 기준.\nCHILD_LIST_FILES = {\n    "2025-12-31": "21_서울_어린이보호구역_지정현황_20251231_목록용.csv",\n    "2026-06-30": "22_서울_어린이보호구역_지정현황_20260630_목록용.csv",\n}\nBUDGET_FILE = "14_서울시예산_2026.csv"\n'

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


def overwrite(path, text):
    target = ROOT / path
    old = target.read_text(encoding="utf-8") if target.exists() else None
    if old == text:
        print(f"이미 최신: {path}")
        return
    write(path, text)
    print(f"{'갱신' if old is not None else '생성'}: {path}")


if not (ROOT / "app" / "main.py").exists():
    raise SystemExit("프로젝트 루트(app 폴더가 있는 곳)에서 실행해 줘.")

missing = [
    name for name in (
        "21_서울_어린이보호구역_지정현황_20251231_목록용.csv",
        "22_서울_어린이보호구역_지정현황_20260630_목록용.csv",
    )
    if not (ROOT / "data" / name).exists()
]
if missing:
    print("data 폴더에 아직 없는 CSV:", ", ".join(missing))
    print("먼저 make_child_zone_list.py로 만들거나 받은 CSV를 data 폴더에 넣어 줘. (코드는 계속 적용할게)")

overwrite("app/services/budget_service.py", SERVICE)
overwrite("tests/test_budget_service.py", TEST)

data_files = read("app/services/data_files.py")
lines = data_files.split("\n")
changed = False
if any(line.startswith("CHILD_YEAREND_FILE") for line in lines):
    lines = [line for line in lines if not line.startswith("CHILD_YEAREND_FILE")]
    changed = True
text = "\n".join(lines)
if "CHILD_LIST_FILES" not in text:
    anchor = 'BUDGET_FILE = "14_서울시예산_2026.csv"\n'
    if anchor in text:
        text = text.replace(anchor, LIST_BLOCK + anchor, 1)
    elif text.count("CHILD_SUMMARY_FILE =") == 1:
        text = text.replace(
            "CHILD_SUMMARY_FILE =",
            LIST_BLOCK + 'BUDGET_FILE = "14_서울시예산_2026.csv"\nCHILD_SUMMARY_FILE =',
            1,
        )
    else:
        raise SystemExit("못 찾음: app/services/data_files.py 의 CHILD_SUMMARY_FILE")
    changed = True
if "BUDGET_FILE" not in text:
    raise SystemExit("data_files.py에 BUDGET_FILE이 없어서 직접 확인해 줘.")
if changed:
    write("app/services/data_files.py", text)
    print("수정: app/services/data_files.py")
else:
    print("이미 적용됨: app/services/data_files.py")

models = read("app/models.py")
if "class BudgetProject" in models:
    head = models[: models.index("class BudgetProject")].rstrip()
    tail = models[models.index("class BudgetProject"):]
    if "class ElderlyBudgetProject" in tail or "zones_2025" not in tail:
        write("app/models.py", head + "\n\n\n" + MODELS_ADD)
        print("갱신: app/models.py")
    else:
        print("이미 최신: app/models.py")
else:
    write("app/models.py", models.rstrip() + "\n\n\n" + MODELS_ADD)
    print("수정: app/models.py")

replace_once("app/main.py", "    ZoneOverview,\n)", "    ZoneBudget,\n    ZoneOverview,\n)", "    ZoneBudget,")
replace_once("app/main.py", "    accident_service,\n", "    accident_service,\n    budget_service,\n", "    budget_service,")
replace_once(
    "app/main.py",
    '@app.get("/api/statistics/hotspots", response_model=Hotspots)',
    ROUTE_CODE + '@app.get("/api/statistics/hotspots", response_model=Hotspots)',
    "/api/budget/zone-improvement",
)

routes = read("tests/test_fastapi_routes.py")
OLD_ASSERT = 'body["elderly_disabled"]["zones"] == 195'
NEW_ASSERT = 'body["elderly_disabled"]["zones_2025"] == 195 and body["child"]["zones_2026"] == 1630'
if "test_zone_budget_endpoint" not in routes:
    write("tests/test_fastapi_routes.py", routes.rstrip() + "\n" + ROUTE_TEST)
    print("수정: tests/test_fastapi_routes.py")
elif OLD_ASSERT in routes or 'body["child"]["zones_2026"] == 1658' in routes:
    write(
        "tests/test_fastapi_routes.py",
        routes.replace(OLD_ASSERT, NEW_ASSERT).replace('body["child"]["zones_2026"] == 1658', 'body["child"]["zones_2026"] == 1630'),
    )
    print("갱신: tests/test_fastapi_routes.py")
else:
    print("이미 최신: tests/test_fastapi_routes.py")

print("끝. data 폴더의 예전 21_서울_어린이보호구역_연말_지정수.csv는 이제 안 써서 지워도 돼.")
print("python -m pytest -q 로 확인하고 uvicorn을 껐다 다시 켜 줘.")

"""서울 어린이보호구역 무인단속카메라 설치 전후 비교(17번)를 서버에 추가한다. 다시 돌려도 안전해.

사용법(프로젝트 루트에서):
    .\\.venv\\Scripts\\python.exe apply_child_camera.py
"""

from pathlib import Path

ROOT = Path.cwd()

CSV = '구분,기간,어린이_보행사고,전체_보행사고,어린이_보행부상자,전체_보행부상자,설치대수,출처\n설치 전,2018~2019,31,133,33,141,107,서울시 보도자료 2023-12-01 (TAAS 도로교통공단 서울지부 분석)\n설치 후,2021~2022,9,66,9,68,107,서울시 보도자료 2023-12-01 (TAAS 도로교통공단 서울지부 분석)\n'
SERVICE_ADD = 'def child_camera_effect(data_dir: Path | str | None = None) -> ChildCameraEffect:\n    """서울 무인단속카메라 설치 전·후 각 2년의 어린이 보행사고."""\n\n    data = read_csv(CHILD_CAMERA_FILE, data_dir)\n    columns = ["구분", "기간", "어린이_보행사고", "어린이_보행부상자", "설치대수"]\n    require_columns(data, CHILD_CAMERA_FILE, columns)\n    if data[columns].isna().any().any():\n        raise ServiceError(f"{CHILD_CAMERA_FILE}에 비어 있는 값이 있어.", 500)\n    rows = {}\n    for label in ("설치 전", "설치 후"):\n        found = data[data["구분"].eq(label)]\n        if len(found) != 1:\n            raise ServiceError(f"{CHILD_CAMERA_FILE}에 \'{label}\' 행이 정확히 하나여야 해.", 500)\n        rows[label] = found.iloc[0]\n    before, after = rows["설치 전"], rows["설치 후"]\n    if before["어린이_보행사고"] <= 0:\n        raise ServiceError("설치 전 사고 건수가 0이라 감소율을 계산할 수 없어.", 500)\n\n    def period(row):\n        return CameraPeriod(\n            period=str(row["기간"]),\n            accidents=int(row["어린이_보행사고"]),\n            injuries=int(row["어린이_보행부상자"]),\n        )\n\n    drop = (before["어린이_보행사고"] - after["어린이_보행사고"]) / before["어린이_보행사고"] * 100\n    return ChildCameraEffect(\n        cameras=int(before["설치대수"]),\n        before=period(before),\n        after=period(after),\n        accidents_reduction_percent=int(drop + 0.5),\n    )\n'
TEST = 'import pytest\n\nfrom app.errors import ServiceError\nfrom app.services import accident_service\nfrom app.services.data_files import CHILD_CAMERA_FILE\n\nHEADER = "구분,기간,어린이_보행사고,전체_보행사고,어린이_보행부상자,전체_보행부상자,설치대수,출처\\n"\n\n\ndef test_reduction_is_rounded(write_csv):\n    data_dir = write_csv(CHILD_CAMERA_FILE, HEADER + "설치 전,2018~2019,3,0,4,0,10,x\\n설치 후,2021~2022,1,0,1,0,10,x")\n    result = accident_service.child_camera_effect(data_dir)\n    assert result.accidents_reduction_percent == 67  # 66.7\n    assert (result.before.period, result.after.accidents, result.cameras) == ("2018~2019", 1, 10)\n\n\ndef test_missing_row_is_error(write_csv):\n    data_dir = write_csv(CHILD_CAMERA_FILE, HEADER + "설치 전,2018~2019,3,0,4,0,10,x")\n    with pytest.raises(ServiceError, match="설치 후"):\n        accident_service.child_camera_effect(data_dir)\n\n\ndef test_real_data_matches_press_release(real_data_dir):\n    result = accident_service.child_camera_effect(real_data_dir)\n    assert (result.before.accidents, result.after.accidents) == (31, 9)\n    assert (result.before.injuries, result.after.injuries) == (33, 9)\n    assert (result.before.period, result.after.period) == ("2018~2019", "2021~2022")\n    assert result.accidents_reduction_percent == 71 and result.cameras == 107\n'
ROUTE_TEST = '\n\ndef test_child_camera_effect_endpoint():\n    body = client.get("/api/traffic/child-camera-effect").json()\n    assert (body["before"]["accidents"], body["after"]["accidents"]) == (31, 9)\n'
MODELS_ADD = 'class CameraPeriod(BaseModel):\n    period: str  # 예: 2018~2019\n    accidents: int = Field(ge=0)  # 어린이 보행사고\n    injuries: int = Field(ge=0)  # 어린이 보행 부상자\n\n\nclass ChildCameraEffect(BaseModel):\n    cameras: int = Field(gt=0)\n    before: CameraPeriod\n    after: CameraPeriod\n    accidents_reduction_percent: int  # 사고 감소율(반올림)\n'
ROUTE_CODE = '@app.get("/api/traffic/child-camera-effect", response_model=ChildCameraEffect)\ndef get_child_camera_effect():\n    return accident_service.child_camera_effect()\n\n\n'


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

target = ROOT / "data" / "20_서울_어린이보호구역_무인단속카메라_전후.csv"
if target.exists():
    print("이미 있음(덮어쓰지 않음): data/20_서울_어린이보호구역_무인단속카메라_전후.csv")
else:
    target.write_text(CSV, encoding="utf-8-sig", newline="\n")
    print("생성: data/20_서울_어린이보호구역_무인단속카메라_전후.csv")
create("tests/test_child_camera_effect.py", TEST)

replace_once(
    "app/services/data_files.py",
    "CHILD_SUMMARY_FILE =",
    'CHILD_CAMERA_FILE = "20_서울_어린이보호구역_무인단속카메라_전후.csv"\nCHILD_SUMMARY_FILE =',
    "CHILD_CAMERA_FILE",
)

models = read("app/models.py")
if "class ChildCameraEffect" in models:
    print("이미 적용됨: app/models.py")
else:
    write("app/models.py", models.rstrip() + "\n\n\n" + MODELS_ADD)
    print("수정: app/models.py")

replace_once(
    "app/services/accident_service.py", "    ChildPedestrian,\n",
    "    CameraPeriod,\n    ChildCameraEffect,\n    ChildPedestrian,\n", "    CameraPeriod,",
)
replace_once(
    "app/services/accident_service.py", "    NATIONAL_DEATHS_FILE,\n    CHILD_SUMMARY_FILE,\n",
    "    NATIONAL_DEATHS_FILE,\n    CHILD_CAMERA_FILE,\n    CHILD_SUMMARY_FILE,\n", "    CHILD_CAMERA_FILE,",
)
service = read("app/services/accident_service.py")
if "def child_camera_effect" in service:
    print("이미 적용됨: 서비스 함수")
else:
    write("app/services/accident_service.py", service.rstrip() + "\n\n\n" + SERVICE_ADD)
    print("수정: app/services/accident_service.py")

replace_once("app/main.py", "    ChildPedestrian,\n", "    ChildCameraEffect,\n    ChildPedestrian,\n", "    ChildCameraEffect,")
replace_once(
    "app/main.py",
    '@app.get("/api/statistics/hotspots", response_model=Hotspots)',
    ROUTE_CODE + '@app.get("/api/statistics/hotspots", response_model=Hotspots)',
    "/api/traffic/child-camera-effect",
)

routes = read("tests/test_fastapi_routes.py")
if "test_child_camera_effect_endpoint" in routes:
    print("이미 적용됨: tests/test_fastapi_routes.py")
else:
    write("tests/test_fastapi_routes.py", routes.rstrip() + "\n" + ROUTE_TEST)
    print("수정: tests/test_fastapi_routes.py")

print("끝. python -m pytest -q 로 확인하고 uvicorn을 껐다 다시 켜 줘.")

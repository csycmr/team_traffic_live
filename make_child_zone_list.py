"""서울시 어린이보호구역 지정현황 엑셀을 data 폴더용 CSV(목록용)로 바꾼다.

사용법(프로젝트 루트에서):
    .\\.venv\\Scripts\\python.exe make_child_zone_list.py "엑셀파일경로.xlsx" [번호]
번호를 안 쓰면 21번이야. 파일명은 엑셀 안의 기준일로 자동으로 정해져.
    예) 기준일 2025-12-31 -> data\\21_서울_어린이보호구역_지정현황_20251231_목록용.csv
"""

import re
import sys
from pathlib import Path

import pandas as pd


def find_sheet(path: Path) -> str:
    names = pd.ExcelFile(path).sheet_names
    for name in names:
        if "지정현황" in name or "세부현황" in name:
            return name
    raise SystemExit(f"지정현황 시트를 못 찾았어. 시트: {names}")


def main(path: Path, number: str) -> int:
    if not path.exists():
        print(f"엑셀 파일을 못 찾았어: {path}")
        return 1
    if not Path("data").is_dir():
        print("프로젝트 루트(data 폴더가 있는 곳)에서 실행해 줘.")
        return 1

    raw = pd.read_excel(path, sheet_name=find_sheet(path), header=None)
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(raw.iloc[1, 6]))
    if not match:
        print(f"기준일을 못 읽었어: {raw.iloc[1, 6]!r}")
        return 1
    year, month, day = (int(part) for part in match.groups())
    date = f"{year:04d}-{month:02d}-{day:02d}"

    # 칸 안의 줄바꿈은 공백 하나로 바꿔서 CSV 한 줄이 시설 한 곳이 되게 해.
    raw = raw.map(lambda value: re.sub(r"\s*\n\s*", " ", value) if isinstance(value, str) else value)
    body = raw.iloc[4:, 1:8].copy()
    body.columns = ["연번", "자치구", "행정동", "도로명주소", "시설명", "시설유형", "지정연도"]
    total = int(body[body["자치구"].eq("합계")].iloc[0]["도로명주소"])
    subtotals = body[body["자치구"].eq("소계")].set_index("행정동")["도로명주소"].astype(int)
    rows = body[pd.to_numeric(body["연번"], errors="coerce").notna()].copy()

    result = pd.DataFrame(
        {
            "기준일": date,
            "자치구": rows["자치구"].str.strip(),
            "행정동": rows["행정동"].astype(str).str.strip(),
            "도로명주소": rows["도로명주소"].astype(str).str.strip(),
            "시설명": rows["시설명"].astype(str).str.strip(),
            "시설유형": rows["시설유형"].str.strip(),
            "지정연도": rows["지정연도"].astype(int),
            "원본연번": rows["연번"].astype(int),
        }
    )

    by_district = result.groupby("자치구").size()
    problems = []
    if len(result) != total:
        problems.append(f"시설 행 수 {len(result)}곳이 합계 {total}곳과 달라.")
    if not by_district.equals(subtotals.reindex(by_district.index)):
        problems.append("자치구별 개수가 소계와 달라.")
    if result.isna().any().any():
        problems.append("빈 칸이 있어.")
    if problems:
        print("엑셀 모양이 예상과 달라서 만들지 않았어:", " ".join(problems))
        return 1

    out = Path("data") / f"{number}_서울_어린이보호구역_지정현황_{date.replace('-', '')}_목록용.csv"
    result.to_csv(out, index=False, encoding="utf-8-sig", lineterminator="\n")
    print(f"만들었어: {out} ({len(result):,}곳, 기준일 {date})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) == 3 else "21"))

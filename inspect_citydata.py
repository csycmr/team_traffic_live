"""서울시 실시간 도시데이터 응답에서 교통·돌발 정보의 실제 구조를 확인한다.

사용 (프로젝트 루트에서):
  .\\.venv\\Scripts\\python.exe inspect_citydata.py                 # 광화문·덕수궁
  .\\.venv\\Scripts\\python.exe inspect_citydata.py "서울역"

- .env의 SEOUL_CITYDATA_API_KEY로 API를 한 번 호출해 구조를 출력한다.
- 인증키는 출력하지 않고 저장하지도 않는다.
- 원본 응답은 citydata_sample_<지역>.xml로 저장한다(공개 데이터라 공유해도 돼).
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.adapters.citydata import fetch_citydata_xml  # noqa: E402
from app.config import load_settings  # noqa: E402

MAX_ROWS = 2  # 같은 이름이 반복되는 행은 앞의 몇 개만 보여준다.


def show(element: ET.Element, depth: int = 0, seen_rows: dict | None = None) -> None:
    pad = "  " * depth
    children = list(element)
    text = (element.text or "").strip()
    if not children:
        print(f"{pad}{element.tag} = {text[:70]!r}")
        return
    print(f"{pad}{element.tag}  (하위 {len(children)}개)")
    counts: dict[str, int] = {}
    for child in children:
        counts[child.tag] = counts.get(child.tag, 0) + 1
        if counts[child.tag] <= MAX_ROWS:
            show(child, depth + 1)
        elif counts[child.tag] == MAX_ROWS + 1:
            print(f"{pad}  … {child.tag} 반복 (이하 생략)")


def main(area: str) -> int:
    key = load_settings().seoul_citydata_api_key
    if not key:
        print(".env에 SEOUL_CITYDATA_API_KEY가 없어.")
        return 1

    raw = fetch_citydata_xml(key, area)
    out = Path(f"citydata_sample_{area}.xml")
    out.write_bytes(raw)
    root = ET.fromstring(raw)

    print("결과 코드:", root.findtext(".//RESULT.CODE"), root.findtext(".//RESULT.MESSAGE"))
    city = root.find(".//CITYDATA")
    if city is None:
        print("CITYDATA가 없어. 지역 이름을 확인해 줘.")
        return 1

    print("\n== CITYDATA 바로 아래 항목 ==")
    for child in city:
        print(" -", child.tag, f"(하위 {len(list(child))}개)")

    print("\n== 교통·돌발·날씨 관련 구조 ==")
    for child in city:
        if any(word in child.tag for word in ("ROAD", "TRAFFIC", "ACDNT", "CNTRL", "WEATHER")):
            show(child)
            print()

    print(f"원본 저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "광화문·덕수궁"))

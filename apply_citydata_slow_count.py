"""서행·정체 구간 목록 아래에 '외 N곳'을 보여 준다.

사용: .\\.venv\\Scripts\\python.exe apply_citydata_slow_count.py seoul-traffic-demo.html
- 서버가 소통이 나쁜 상위 10개 구간만 보내므로, 전체 개수(slowSegmentCount)가 더 크면
  목록 끝에 '외 N곳' 한 줄을 붙인다. 디자인(클래스)은 기존 것을 그대로 쓴다.
- 이미 적용돼 있으면 건너뛴다. 원본은 seoul-traffic-demo.html.bak으로 남긴다.
"""

import shutil
import sys
from pathlib import Path

REPLACEMENTS = [
    (
        "renderSlowRoads(data.traffic?.slowSegments);",
        "renderSlowRoads(data.traffic?.slowSegments, data.traffic?.slowSegmentCount);",
    ),
    (
        "function renderSlowRoads(segments) {",
        "function renderSlowRoads(segments, total) {",
    ),
    (
        "  container.replaceChildren(list);\n",
        "  container.replaceChildren(list);\n"
        "  if (Number.isFinite(total) && total > segments.length) {\n"
        "    const more = document.createElement('p');\n"
        "    more.className = 'muted';\n"
        "    more.textContent = `외 ${(total - segments.length).toLocaleString('ko-KR')}곳`;\n"
        "    container.append(more);\n"
        "  }\n",
    ),
]


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")

    if "total > segments.length" in text:
        print("이미 적용됨  : 서행·정체 '외 N곳'")
        return 0

    for old, _ in REPLACEMENTS:
        count = text.count(old)
        if count != 1:
            print(f"못 찾음({count}곳) : {old.strip()}")
            return 1

    shutil.copyfile(path, path.with_name(path.name + ".bak"))
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("추가         : 서행·정체 '외 N곳'")
    print(f"저장했어. 원본은 {path.name}.bak")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))

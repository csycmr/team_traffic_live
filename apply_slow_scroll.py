"""서행/정체 구간 목록이 길면 목록 영역 안에서 스크롤되게 한다.

사용: .\\.venv\\Scripts\\python.exe apply_slow_scroll.py seoul-traffic-demo.html
- #slow-roads-list에 최대 높이와 내부 스크롤을 준다(사고·통제 알림 목록과 같은 방식).
- 목록은 5초마다 다시 그려지므로 스크롤 위치를 유지한다.
- 키보드로도 스크롤할 수 있게 tabindex="0"과 aria-label을 붙인다.
- 이미 적용돼 있으면 건너뛴다. 원본은 seoul-traffic-demo.html.bak으로 남긴다.
"""

import shutil
import sys
from pathlib import Path

REPLACEMENTS = [
    (
        '#slow-roads-list p, #slow-roads-list ul { margin: 4px 0 0; font-size: 12px }\n',
        '#slow-roads-list p, #slow-roads-list ul { margin: 4px 0 0; font-size: 12px }\n'
        '#slow-roads-list { max-height: 260px; overflow-y: auto; padding-inline-end: 4px }\n',
    ),
    (
        '<div id="slow-roads-list">',
        '<div id="slow-roads-list" tabindex="0" aria-label="서행·정체 구간 목록">',
    ),
    (
        "  const container = byId('slow-roads-list');\n",
        "  const container = byId('slow-roads-list');\n"
        "  const previousScroll = container.scrollTop; // 5초마다 다시 그려도 읽던 위치를 유지한다.\n",
    ),
    (
        "  container.replaceChildren(list);\n",
        "  container.replaceChildren(list);\n  container.scrollTop = previousScroll;\n",
    ),
]


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")

    if "previousScroll" in text:
        print("이미 적용됨  : 서행·정체 목록 내부 스크롤")
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
    print("추가         : 서행·정체 목록 내부 스크롤")
    print(f"저장했어. 원본은 {path.name}.bak")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))

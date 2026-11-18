"""seoul-traffic-demo.html의 노인 교통사고율 카드를 FastAPI 값에 연결한다.

사용: .\\.venv\\Scripts\\python.exe apply_elderly_rates.py seoul-traffic-demo.html
- 바꿀 문자열을 찾아서 id를 붙이고 loadElderlyRates()를 추가한다.
- 이미 적용된 항목은 건너뛰고, 못 찾은 항목은 따로 알려준다. 여러 번 실행해도 안전하다.
- 원본은 seoul-traffic-demo.html.bak으로 남긴다.
"""

import re
import shutil
import sys
from pathlib import Path

REPLACEMENTS = [
    (
        "전년 대비 사고 문구",
        r'<div class="stat-change">전년 대비 \+97건</div>',
        '<div class="stat-change" id="elderly-accidents-change">전년 대비 —건</div>',
        "elderly-accidents-change",
    ),
    (
        "전년 대비 사망 문구",
        r'<div class="stat-change">전년 대비 \+14명</div>',
        '<div class="stat-change" id="elderly-deaths-change">전년 대비 —명</div>',
        "elderly-deaths-change",
    ),
    (
        "고령인구 1만 명당 카드",
        r"<dd><strong>10\.77</strong><small>건</small></dd>",
        '<dd><strong id="elderly-accident-rate">—</strong><small>건</small></dd>',
        "elderly-accident-rate",
    ),
    (
        "전체 보행 사망자 중 고령층 카드",
        r"<dd><strong>67\.2</strong><small>%</small></dd>",
        '<dd><strong id="elderly-death-share">—</strong><small>%</small></dd>',
        "elderly-death-share",
    ),
    (
        "자치구 표 서울시 평균",
        r'<span class="district-average-label">서울시 평균 10\.77</span>',
        '<span class="district-average-label" id="district-average-rate">서울시 평균 —</span>',
        "district-average-rate",
    ),
    (
        "차트 설명의 사고율",
        r"<strong>10\.77건</strong> · 2024년 대비",
        '<strong id="elderly-rate-caption">—건</strong> · 2024년 대비',
        "elderly-rate-caption",
    ),
]

SCRIPT = """
  async function loadElderlyRates() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/elderly"
      );

      if (!response.ok) {
        throw new Error(`고령 보행사고 API 응답 오류: ${response.status}`);
      }

      const elderly = await response.json();
      const numbers = [
        elderly.accidents_per_10k,
        elderly.death_share_percent,
        elderly.accidents_change,
        elderly.deaths_change
      ];

      if (!numbers.every(Number.isFinite)) {
        throw new Error("고령 보행사고 API 값을 확인해 줘.");
      }

      const formatCount = new Intl.NumberFormat("ko-KR");
      const formatChange = (value, unit) =>
        `전년 대비 ${value > 0 ? "+" : value < 0 ? "−" : ""}${formatCount.format(Math.abs(value))}${unit}`;
      const rate = elderly.accidents_per_10k.toFixed(2);
      const setText = (id, text) => {
        const element = document.getElementById(id);
        if (element) element.textContent = text;
      };

      setText("elderly-accident-rate", rate);
      setText("elderly-death-share", elderly.death_share_percent.toFixed(1));
      setText("elderly-accidents-change", formatChange(elderly.accidents_change, "건"));
      setText("elderly-deaths-change", formatChange(elderly.deaths_change, "명"));
      setText("district-average-rate", `서울시 평균 ${rate}`);
      setText("elderly-rate-caption", `${rate}건`);

      console.info("고령 보행사고 사고율 API 연결 완료", elderly.year);
    } catch (error) {
      console.error("고령 보행사고 사고율을 불러오지 못했어.", error);
    }
  }

  loadElderlyRates();
"""


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    original = text
    missing = []

    for label, pattern, replacement, marker in REPLACEMENTS:
        if f'id="{marker}"' in text:
            print(f"이미 적용됨  : {label}")
        elif re.search(pattern, text):
            text = re.sub(pattern, replacement, text, count=1)
            print(f"바꿈         : {label}")
        else:
            missing.append(label)
            print(f"못 찾음      : {label}")

    if "loadElderlyRates" in text:
        print("이미 적용됨  : loadElderlyRates()")
    else:
        end = text.rfind("</script>")
        if end == -1 or "</body>" not in text[end:]:
            missing.append("loadElderlyRates() 넣을 위치(</body> 앞 마지막 script)")
            print("못 찾음      : loadElderlyRates() 넣을 위치")
        else:
            text = text[:end].rstrip("\n") + "\n" + SCRIPT + text[end:]
            print("추가         : loadElderlyRates()")

    if text != original:
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
        path.write_text(text, encoding="utf-8")
        print(f"\n저장했어. 원본은 {path.name}.bak")
    else:
        print("\n바뀐 내용이 없어.")

    if missing:
        print("\n직접 확인할 항목:", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))

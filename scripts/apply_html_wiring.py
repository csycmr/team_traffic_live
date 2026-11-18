"""seoul-traffic-demo.html에 FastAPI·Flask 연결 코드를 한 번에 적용한다.

사용 (프로젝트 루트에서):
  .\\.venv\\Scripts\\python.exe scripts\\apply_html_wiring.py
  .\\.venv\\Scripts\\python.exe scripts\\apply_html_wiring.py 다른파일.html

아래 단계를 순서대로 적용한다. 이미 적용된 단계는 건너뛰어서 여러 번 실행해도 안전하다.
  1. 노인 교통사고율 카드      → /api/statistics/elderly
  2. 자치구 사고율 표 두 개     → /api/statistics/elderly/districts
  3. 전국 사망자 막대          → /api/traffic/national-deaths
  4. 서행·정체 '외 N곳' 표시   (실시간 교통 카드)
  5. 서행·정체 목록 내부 스크롤 (실시간 교통 카드)
바뀐 내용이 있으면 원본을 <파일>.bak으로 한 번만 남긴다. 못 찾은 단계가 있으면 종료 코드 1로 끝난다.
"""

import re
import shutil
import sys
from pathlib import Path

HTML_NAME = "seoul-traffic-demo.html"


def default_html() -> Path:
    """프로젝트 루트나 scripts/ 어느 쪽에 두고 실행해도 HTML을 찾는다."""
    here = Path(__file__).resolve().parent
    for folder in (Path.cwd(), here, here.parent):
        if (folder / HTML_NAME).exists():
            return folder / HTML_NAME
    return Path.cwd() / HTML_NAME

# ── 1. 노인 교통사고율 카드 ─────────────────────────────
ELDERLY_REPLACEMENTS = [('전년 대비 사고 문구',
  '<div class="stat-change">전년 대비 \\+97건</div>',
  '<div class="stat-change" id="elderly-accidents-change">전년 대비 —건</div>',
  'elderly-accidents-change'),
 ('전년 대비 사망 문구',
  '<div class="stat-change">전년 대비 \\+14명</div>',
  '<div class="stat-change" id="elderly-deaths-change">전년 대비 —명</div>',
  'elderly-deaths-change'),
 ('고령인구 1만 명당 카드',
  '<dd><strong>10\\.77</strong><small>건</small></dd>',
  '<dd><strong id="elderly-accident-rate">—</strong><small>건</small></dd>',
  'elderly-accident-rate'),
 ('전체 보행 사망자 중 고령층 카드',
  '<dd><strong>67\\.2</strong><small>%</small></dd>',
  '<dd><strong id="elderly-death-share">—</strong><small>%</small></dd>',
  'elderly-death-share'),
 ('자치구 표 서울시 평균',
  '<span class="district-average-label">서울시 평균 10\\.77</span>',
  '<span class="district-average-label" id="district-average-rate">서울시 평균 —</span>',
  'district-average-rate'),
 ('차트 설명의 사고율',
  '<strong>10\\.77건</strong> · 2024년 대비',
  '<strong id="elderly-rate-caption">—건</strong> · 2024년 대비',
  'elderly-rate-caption')]

ELDERLY_SCRIPT = """
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

# ── 2. 자치구 사고율 표 ────────────────────────────────
DISTRICT_SCRIPT = """
  async function loadDistrictRates() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/elderly/districts"
      );

      if (!response.ok) {
        throw new Error(`자치구 사고율 API 응답 오류: ${response.status}`);
      }

      const { districts } = await response.json();
      const riskBody = document.querySelector("#district-risk .zone-data-table tbody");
      const changeBody = document.querySelector("#district-change .risk-change-table tbody");

      if (!riskBody || !changeBody || !Array.isArray(districts) || districts.length !== 25) {
        throw new Error("자치구 표나 API 값을 확인해 줘.");
      }

      const formatCount = new Intl.NumberFormat("ko-KR");
      // 부호를 붙인다. 0은 부호 없이 표시한다. 기존 표처럼 음수는 반각 하이픈이야.
      const signed = (value, digits = 0) =>
        value === 0 ? (0).toFixed(digits) : `${value > 0 ? "+" : "-"}${Math.abs(value).toFixed(digits)}`;
      const escapeHtml = (text) =>
        String(text).replace(/[&<>"']/g, (char) => (
          { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
        ));

      riskBody.innerHTML = districts.map((row) => `
            <tr>
              <th scope="row">${escapeHtml(row.district)}</th><td>${formatCount.format(row.population_65plus)}</td><td>${row.accidents}</td><td>${row.hotspots}</td><td>${row.protection_zones}</td><td>${row.overlaps}</td>
              <td class="district-rate">${row.accidents_per_10k.toFixed(2)}</td>
              <td><span class="district-track" aria-hidden="true"><span style="--rate:${row.bar_percent.toFixed(2)}%"></span></span></td>
            <td class="district-name-end">${escapeHtml(row.district)}</td></tr>`).join("");

      changeBody.innerHTML = districts.map((row) => {
        const percent = row.accidents_change_percent === null
          ? "—"
          : signed(row.accidents_change_percent, 1);
        return `
          <tr><th scope="row">${escapeHtml(row.district)}</th><td>${row.rank}</td><td>${row.previous_rank}</td><td>${signed(row.rank_change)}</td><td>${row.accidents_per_10k.toFixed(2)}</td><td>${signed(row.rate_gap, 2)}</td><td>${signed(row.accidents_change)}</td><td>${percent}</td><td class="district-name-end">${escapeHtml(row.district)}</td></tr>`;
      }).join("");

      console.info("자치구 고령 보행사고율 API 연결 완료", districts.length);
    } catch (error) {
      console.error("자치구 고령 보행사고율을 불러오지 못했어.", error);
    }
  }

  loadDistrictRates();
"""

# ── 3. 전국 사망자 막대 ────────────────────────────────
NATIONAL_SCRIPT = """
  async function loadNationalDeaths() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/traffic/national-deaths"
      );

      if (!response.ok) {
        throw new Error(`전국 사망자 API 응답 오류: ${response.status}`);
      }

      const { years } = await response.json();
      const items = new Map(
        [...document.querySelectorAll(".national-years .national-year")].map((item) => [
          item.querySelector(".national-year-label")?.textContent.trim(),
          item,
        ])
      );

      if (!Array.isArray(years) || years.length === 0 || years.length !== items.size) {
        throw new Error("전국 사망자 막대 수와 API 연도 수가 달라.");
      }

      const formatCount = new Intl.NumberFormat("ko-KR");
      const AXIS_MAX = 3500; // 막대 높이 100%에 해당하는 사망자 수(눈금 3,000이 85.7%)

      years.forEach((row) => {
        const item = items.get(`${row.year}년`);

        if (!item) {
          throw new Error(`${row.year}년 막대를 찾지 못했어.`);
        }

        item.querySelector(".national-year-total").innerHTML =
          `<span class="oecd-sr">전체 </span>${formatCount.format(row.total_deaths)}명`;
        item.style.setProperty("--total", `${(row.total_deaths / AXIS_MAX) * 100}%`);

        // 65세 이상 값은 OECD 자료가 있는 연도에만 온다. null이면 화면 값을 유지한다.
        if (row.elderly_deaths !== null && row.elderly_share_percent !== null) {
          item.querySelector(".national-older").innerHTML = `
                  <span><span class="oecd-sr">65세 이상 </span>${formatCount.format(row.elderly_deaths)}명</span>
                  <strong><span class="oecd-sr">비중 </span>${row.elderly_share_percent.toFixed(1)}%</strong>`;
          item.style.setProperty("--older", `${(row.elderly_deaths / row.total_deaths) * 100}%`);
        }
      });

      const first = years[0];
      const leadFirst = document.querySelector(".national-lead strong");

      if (leadFirst && first.elderly_share_percent !== null) {
        leadFirst.textContent = `${first.elderly_share_percent.toFixed(1)}%`;
      }

      console.info("전국 사망자 API 연결 완료", years.length);
    } catch (error) {
      console.error("전국 사망자 막대를 불러오지 못했어.", error);
    }
  }

  loadNationalDeaths();
"""

# ── 4·5. 실시간 교통 카드(서행·정체 목록) ─────────────────
SLOW_COUNT_REPLACEMENTS = [('renderSlowRoads(data.traffic?.slowSegments);',
  'renderSlowRoads(data.traffic?.slowSegments, data.traffic?.slowSegmentCount);'),
 ('function renderSlowRoads(segments) {', 'function renderSlowRoads(segments, total) {'),
 ('  container.replaceChildren(list);\n',
  '  container.replaceChildren(list);\n'
  '  if (Number.isFinite(total) && total > segments.length) {\n'
  "    const more = document.createElement('p');\n"
  "    more.className = 'muted';\n"
  "    more.textContent = `외 ${(total - segments.length).toLocaleString('ko-KR')}곳`;\n"
  '    container.append(more);\n'
  '  }\n')]

SLOW_SCROLL_REPLACEMENTS = [('#slow-roads-list p, #slow-roads-list ul { margin: 4px 0 0; font-size: 12px }\n',
  '#slow-roads-list p, #slow-roads-list ul { margin: 4px 0 0; font-size: 12px }\n'
  '#slow-roads-list { max-height: 260px; overflow-y: auto; padding-inline-end: 4px }\n'),
 ('<div id="slow-roads-list">', '<div id="slow-roads-list" tabindex="0" aria-label="서행·정체 구간 목록">'),
 ("  const container = byId('slow-roads-list');\n",
  "  const container = byId('slow-roads-list');\n"
  '  const previousScroll = container.scrollTop; // 5초마다 다시 그려도 읽던 위치를 유지한다.\n'),
 ('  container.replaceChildren(list);\n',
  '  container.replaceChildren(list);\n  container.scrollTop = previousScroll;\n')]


def append_script(text, marker, script, required, label):
    """마지막 </script> 앞에 함수를 추가한다. (새 텍스트, 상태)를 돌려준다."""
    if marker in text:
        return text, "skip"
    for needle in required:
        if needle not in text:
            return text, f"못 찾음({needle})"
    end = text.rfind("</script>")
    if end == -1 or "</body>" not in text[end:]:
        return text, "못 찾음(</body> 앞 마지막 script)"
    return text[:end].rstrip("\n") + "\n" + script + text[end:], "apply"


def replace_exact(text, marker, replacements):
    """정확히 한 번 나오는 문자열만 바꾼다."""
    if marker in text:
        return text, "skip"
    for old, _ in replacements:
        count = text.count(old)
        if count != 1:
            return text, f"못 찾음({count}곳: {old.strip()[:40]})"
    for old, new in replacements:
        text = text.replace(old, new)
    return text, "apply"


def step_elderly(text):
    notes = []
    for label, pattern, replacement, marker in ELDERLY_REPLACEMENTS:
        if f'id="{marker}"' in text:
            notes.append("skip")
        elif re.search(pattern, text):
            text = re.sub(pattern, replacement, text, count=1)
            notes.append("apply")
        else:
            notes.append(f"못 찾음({label})")
    text, status = append_script(text, "loadElderlyRates", ELDERLY_SCRIPT, [], "")
    notes.append(status)
    bad = [note for note in notes if note.startswith("못 찾음")]
    if bad:
        return text, bad[0]
    return text, "apply" if "apply" in notes else "skip"


STEPS = [
    ("노인 교통사고율 카드", step_elderly),
    (
        "자치구 사고율 표",
        lambda t: append_script(
            t, "loadDistrictRates", DISTRICT_SCRIPT,
            ['id="district-risk"', 'id="district-change"'], "",
        ),
    ),
    (
        "전국 사망자 막대",
        lambda t: append_script(
            t, "loadNationalDeaths", NATIONAL_SCRIPT,
            ['class="national-years"', 'class="national-lead"'], "",
        ),
    ),
    (
        "서행·정체 '외 N곳'",
        lambda t: replace_exact(t, "total > segments.length", SLOW_COUNT_REPLACEMENTS),
    ),
    (
        "서행·정체 내부 스크롤",
        lambda t: replace_exact(t, "previousScroll", SLOW_SCROLL_REPLACEMENTS),
    ),
]


def main(path: Path) -> int:
    if not path.exists():
        print(f"파일을 찾지 못했어: {path}")
        print("프로젝트 루트에서 실행하거나 HTML 경로를 인자로 넘겨줘.")
        return 1
    text = path.read_text(encoding="utf-8")
    original = text
    failed = []

    for number, (name, step) in enumerate(STEPS, 1):
        text, status = step(text)
        label = {"apply": "적용", "skip": "이미 적용됨"}.get(status, status)
        print(f"{number}. {name:<16} {label}")
        if status not in ("apply", "skip"):
            failed.append(name)

    if text != original:
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
        path.write_text(text, encoding="utf-8")
        print(f"\n저장했어. 원본은 {path.name}.bak")
    else:
        print("\n바뀐 내용이 없어.")

    if failed:
        print("\n직접 확인할 단계:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) == 2 else default_html()))

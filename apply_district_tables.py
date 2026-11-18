"""seoul-traffic-demo.html의 자치구 표 두 개를 FastAPI 값으로 채운다.

사용: .\\.venv\\Scripts\\python.exe apply_district_tables.py seoul-traffic-demo.html
- 자치구별 고령 보행자 사고율 표(#district-risk)와 사고율·전년 변화 표(#district-change)의
  tbody를 /api/statistics/elderly/districts 응답으로 다시 그리는 loadDistrictRates()를 추가한다.
- 기존 표 마크업과 CSS 클래스를 그대로 써서 디자인과 막대 애니메이션은 달라지지 않는다.
- 이미 적용돼 있으면 건너뛴다. 원본은 seoul-traffic-demo.html.bak으로 남긴다.
"""

import shutil
import sys
from pathlib import Path

SCRIPT = """
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


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")

    if "loadDistrictRates" in text:
        print("이미 적용됨  : loadDistrictRates()")
        return 0

    for marker in ('id="district-risk"', 'id="district-change"'):
        if marker not in text:
            print(f"못 찾음      : {marker} (표를 감싼 영역 id)")
            return 1

    end = text.rfind("</script>")
    if end == -1 or "</body>" not in text[end:]:
        print("못 찾음      : </body> 앞 마지막 script")
        return 1

    shutil.copyfile(path, path.with_name(path.name + ".bak"))
    path.write_text(text[:end].rstrip("\n") + "\n" + SCRIPT + text[end:], encoding="utf-8")
    print("추가         : loadDistrictRates()")
    print(f"저장했어. 원본은 {path.name}.bak")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))

"""seoul-traffic-demo.html의 '전체 사망자와 65세 이상 비중' 막대를 FastAPI 값으로 채운다.

사용: .\\.venv\\Scripts\\python.exe apply_national_deaths.py seoul-traffic-demo.html
- /api/traffic/national-deaths 응답으로 연도별 막대 높이(--total), 전체 사망자,
  65세 이상 사망자·비중(--older)과 머리글의 2020년 비중을 바꾸는 loadNationalDeaths()를 추가한다.
- 65세 이상 값이 null인 연도(2024·2025, OECD 자료 없음)는 화면의 기존 값을 그대로 둔다.
- 기존 마크업과 CSS 클래스를 그대로 써서 디자인은 달라지지 않는다.
- 이미 적용돼 있으면 건너뛴다. 원본은 seoul-traffic-demo.html.bak으로 남긴다.
"""

import shutil
import sys
from pathlib import Path

SCRIPT = """
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


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")

    if "loadNationalDeaths" in text:
        print("이미 적용됨  : loadNationalDeaths()")
        return 0

    for marker in ('class="national-years"', 'class="national-lead"'):
        if marker not in text:
            print(f"못 찾음      : {marker}")
            return 1

    end = text.rfind("</script>")
    if end == -1 or "</body>" not in text[end:]:
        print("못 찾음      : </body> 앞 마지막 script")
        return 1

    shutil.copyfile(path, path.with_name(path.name + ".bak"))
    path.write_text(text[:end].rstrip("\n") + "\n" + SCRIPT + text[end:], encoding="utf-8")
    print("추가         : loadNationalDeaths()")
    print(f"저장했어. 원본은 {path.name}.bak")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))

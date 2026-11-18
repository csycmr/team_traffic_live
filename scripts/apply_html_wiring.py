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
  6. 전국 65세 이상 주민등록인구 추이 → /api/statistics/elderly-population
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

# ── 6. 전국 65세 이상 주민등록인구 추이 ───────────────────
POPULATION_SCRIPT = """
  async function loadElderlyPopulation() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/elderly-population"
      );

      if (!response.ok) {
        throw new Error(`65세 이상 인구 API 응답 오류: ${response.status}`);
      }

      const { points } = await response.json();
      const svg = document.querySelector(".national-population svg");

      if (!svg || !Array.isArray(points) || points.length < 2) {
        throw new Error("65세 이상 인구 그래프나 API 값을 확인해 줘.");
      }

      const SVG_NS = "http://www.w3.org/2000/svg";
      const formatCount = new Intl.NumberFormat("ko-KR");
      // 기존 그래프의 좌표 규칙: 첫·끝 점의 x는 82·478, y 눈금은 900만 명=85, 100만 명당 25.5.
      const FIRST_X = 82;
      const LAST_X = 478;
      const yOf = (population) => 85 - (population / 10000 - 900) * 0.255;
      const make = (name, attributes = {}, text = "") => {
        const element = document.createElementNS(SVG_NS, name);
        Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
        if (text) element.textContent = text;
        return element;
      };

      const shapes = points.map((point, index) => ({
        x: Number((FIRST_X + ((LAST_X - FIRST_X) * index) / (points.length - 1)).toFixed(2)),
        y: Number(yOf(point.population).toFixed(2)),
        title: `${point.year}년 ${point.month}월 말 ${formatCount.format(point.population)}명`,
        value: formatCount.format(Math.round(point.population / 10000)),
        label: point.month === 12 ? `${point.year}년` : `${point.year}년 ${point.month}월`,
      }));

      svg.querySelector("polyline").setAttribute(
        "points",
        shapes.map((shape) => `${shape.x},${shape.y}`).join(" ")
      );
      svg.querySelectorAll("g").forEach((group) => group.remove());
      shapes.forEach((shape) => {
        const group = make("g");
        group.append(
          make("title", {}, shape.title),
          make("circle", { cx: shape.x, cy: shape.y, r: 4 }),
          make("text", { class: "population-value", x: shape.x, y: Number((shape.y - 8).toFixed(2)) }, shape.value),
          make("text", { x: shape.x, y: 105 }, shape.label)
        );
        svg.append(group);
      });
      svg.setAttribute("aria-label", shapes.map((shape) => shape.title).join(", "));

      console.info("65세 이상 주민등록인구 API 연결 완료", points.length);
    } catch (error) {
      console.error("65세 이상 주민등록인구를 불러오지 못했어.", error);
    }
  }

  loadElderlyPopulation();
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


ZONE_BEFORE_AFTER_SCRIPT = """
  async function loadZoneBeforeAfter() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/elderly/zone-before-after"
      );

      if (!response.ok) {
        throw new Error(`지정 전후 비교 API 응답 오류: ${response.status}`);
      }

      const data = await response.json();
      const section = document.querySelector("#zone-before-after");
      const body = section && section.querySelector(".risk-change-table tbody");
      const heading = section && section.querySelector(".audit-heading");
      const caption = section && section.querySelector(".audit-chart-caption");

      if (!body || !heading || !caption || !Array.isArray(data.cases) || data.cases.length === 0) {
        throw new Error("지정 전후 표나 API 값을 확인해 줘.");
      }

      // 기존 표처럼 음수는 유니코드 마이너스(−)로, 0은 부호 없이 보여 준다.
      const signed = (value) => (value === 0 ? "0" : `${value > 0 ? "+" : "−"}${Math.abs(value)}`);
      const escapeHtml = (text) =>
        String(text).replace(/[&<>"']/g, (char) => (
          { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
        ));

      body.innerHTML = data.cases.map((row) => `
            <tr><th scope="row">${escapeHtml(row.district)}</th><td>${row.designated_year}</td><td>${row.zones}곳</td><td>${row.accidents_before} → ${row.accidents_at} → ${row.accidents_after}</td><td>${signed(row.accidents_change)}</td><td>${row.rate_before.toFixed(2)} → ${row.rate_at.toFixed(2)} → ${row.rate_after.toFixed(2)}</td></tr>`).join("");
      heading.textContent = `${data.districts}개 자치구 · ${data.cases.length}개 지정 사례`;
      caption.textContent = `자치구 전체 사고 건수 기준 · 증가 ${data.increased}개 · 감소 ${data.decreased}개 · 동일 ${data.unchanged}개`;

      console.info("노인보호구역 지정 전후 API 연결 완료", data.cases.length);
    } catch (error) {
      console.error("노인보호구역 지정 전후 비교를 불러오지 못했어.", error);
    }
  }

  loadZoneBeforeAfter();
"""


COMPARISON_SCRIPT = """
  async function loadDistrictComparison() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/elderly/district-comparison"
      );

      if (!response.ok) {
        throw new Error(`자치구 비교 API 응답 오류: ${response.status}`);
      }

      const { years, series } = await response.json();
      const section = document.querySelector("#district-comparison");
      const rateSvg = section && section.querySelector('[data-risk-plot="rate"] svg');
      const countSvg = section && section.querySelector('[data-risk-plot="count"] svg');
      const tableBody = section && section.querySelector(".risk-comparison-data tbody");

      if (!rateSvg || !countSvg || !tableBody || !Array.isArray(series) || series.length !== 3 || years.length !== 4) {
        throw new Error("비교 차트나 API 값을 확인해 줘.");
      }

      // 그래프 축은 화면에 고정돼 있다. 사고율 0~25건, 사고 건수 0~2,500건이고 y 420(0) ~ 60(최댓값)이야.
      const plots = [
        // 점 위치는 반올림 전 사고율(사고 ÷ 인구 × 10,000)로 잡고, 적히는 숫자는 반올림한 값을 쓴다.
        {
          svg: rateSvg, max: 25,
          value: (point) => (point.accidents / point.population_65plus) * 10000,
          label: (point) => point.accidents_per_10k.toFixed(2),
        },
        {
          svg: countSvg, max: 2500,
          value: (point) => point.accidents,
          label: (point) => point.accidents.toLocaleString("ko-KR"),
        },
      ];
      const firstX = 100;
      const lastX = 955;

      for (const plot of plots) {
        const groups = plot.svg.querySelectorAll("g[style*='--child-series-color']");
        if (groups.length !== series.length) {
          throw new Error("차트의 계열 개수가 API와 달라.");
        }
        series.forEach((item, seriesIndex) => {
          const shapes = item.points.map((point, index) => {
            const value = plot.value(point);
            if (value > plot.max) {
              throw new Error(`${item.name} ${point.year}년 값이 그래프 축(${plot.max})보다 커. 축을 늘려 줘.`);
            }
            const x = firstX + ((lastX - firstX) * index) / (years.length - 1);
            const y = 420 - (value / plot.max) * 360;
            // 맨 아래 계열은 값이 아래쪽에 적혀 서로 겹치지 않게 한다. 기존 화면과 같아.
            const labelY = seriesIndex === series.length - 1 ? y + 23 : y - 14;
            return { x, y, labelY, text: plot.label(point) };
          });
          groups[seriesIndex].innerHTML =
            `<polyline pathLength="1" points="${shapes.map((s) => `${s.x},${s.y}`).join(" ")}"/>` +
            shapes.map((s) =>
              `<circle cx="${s.x}" cy="${s.y}" r="4"/><text class="child-value" x="${s.x}" y="${s.labelY}">${s.text}</text>`
            ).join("");
        });
      }

      const formatCount = new Intl.NumberFormat("ko-KR");
      const escapeHtml = (text) =>
        String(text).replace(/[&<>"']/g, (char) => (
          { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
        ));
      tableBody.innerHTML = years.map((year, index) => series.map((item) => {
        const point = item.points[index];
        return `<tr><th scope="row">${year}</th><td>${escapeHtml(item.name)}</td><td>${formatCount.format(point.population_65plus)}</td><td>${formatCount.format(point.accidents)}</td><td>${point.accidents_per_10k.toFixed(2)}</td></tr>`;
      }).join("\\n")).join("\\n");

      console.info("자치구 비교 추이 API 연결 완료", series.length);
    } catch (error) {
      console.error("자치구 비교 추이를 불러오지 못했어.", error);
    }
  }

  loadDistrictComparison();
"""


HOTSPOT_REVIEW_SCRIPT = """
  async function loadHotspotReview() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/statistics/hotspots/review"
      );

      if (!response.ok) {
        throw new Error(`사고다발지역 검토 API 응답 오류: ${response.status}`);
      }

      const review = await response.json();
      const overlap = document.querySelector("#zone-overlap");
      const section = document.querySelector("#zone-review");
      const counts = overlap && overlap.querySelectorAll(".overlap-counts dd");
      const topBody = section && section.querySelector(".review-list > .review-table-wrap tbody");
      const restBody = section && section.querySelector(".review-details tbody");
      const restTitle = section && section.querySelector(".review-details summary");
      const chartSection = section && section.querySelector("[aria-labelledby='review-chart-title']");
      const chartList = chartSection && chartSection.querySelector(".review-chart ol");
      const chartCaption = chartSection && chartSection.querySelector(".audit-chart-caption");
      const chartSource = chartSection && chartSection.querySelector(".review-source");
      const candidateBody = section && section.querySelector(".review-candidates tbody");

      if (!counts || counts.length !== 3 || !topBody || !restBody || !restTitle || !chartList
          || !chartCaption || !chartSource || !candidateBody || !Array.isArray(review.items)) {
        throw new Error("검토 자료 표나 API 값을 확인해 줘.");
      }

      // 막대 그래프 세로 축이 0~10곳으로 고정돼 있어서, 넘으면 조용히 잘리지 않게 알려 준다.
      const tallest = Math.max(...review.districts.map((d) => d.overlapping + d.outside));
      if (tallest > 10) {
        throw new Error(`자치구 막대(${tallest}곳)가 그래프 축(10곳)보다 커. 축을 늘려 줘.`);
      }

      const escapeHtml = (text) =>
        String(text).replace(/[&<>"']/g, (char) => (
          { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
        ));
      const rowHtml = (item) => {
        const distance = item.overlaps
          ? '<span class="review-badge">겹침</span>'
          : `${item.distance_m.toLocaleString("ko-KR")}m`;
        return `
          <tr><th scope="row">${escapeHtml(item.name)}</th><td>${item.crashes}건</td><td>${distance}</td></tr>`;
      };

      counts[0].textContent = `${review.total}곳`;
      counts[1].textContent = `${review.overlapping}곳`;
      counts[2].textContent = `${review.outside}곳`;

      const topCount = 12;
      topBody.innerHTML = review.items.slice(0, topCount).map(rowHtml).join("");
      restBody.innerHTML = review.items.slice(topCount).map(rowHtml).join("");
      restTitle.textContent = `나머지 ${Math.max(review.items.length - topCount, 0)}곳 자료 표 보기`;

      chartList.innerHTML = review.districts.map((d) => `
            <li aria-label="${escapeHtml(d.district)}, 겹침 ${d.overlapping}곳, 보호구역 밖 ${d.outside}곳"><div class="review-stack" aria-hidden="true"><span class="review-inside" style="--count:${d.overlapping}">${d.overlapping || ""}</span><span class="review-outside" style="--count:${d.outside}">${d.outside || ""}</span></div><span aria-hidden="true">${escapeHtml(d.district)}</span></li>`).join("");
      chartCaption.textContent =
        `${review.year}년 사고다발지역 선정 영역 수(곳) · 선정 지역이 있는 ${review.districts.length}개 자치구`;
      chartSource.innerHTML =
        `판정 가능한 ${review.total}곳 중 보호구역 밖은 <strong>${review.outside}곳(${review.outside_percent.toFixed(1)}%)</strong>입니다.`;

      candidateBody.innerHTML = review.candidates.map((c) => `
          <tr><th scope="row">${escapeHtml(c.district)}</th><td>${c.selected}</td><td>${c.outside}</td><td>${c.overlapping}</td><td>${c.undetermined}</td><td>${c.accidents_per_10k.toFixed(2)}</td></tr>`).join("");

      console.info("사고다발지역 검토 API 연결 완료", review.items.length);
    } catch (error) {
      console.error("사고다발지역 검토 자료를 불러오지 못했어.", error);
    }
  }

  loadHotspotReview();
"""

HOTSPOT_MAP_REPLACEMENTS = [
  ('fetch("./data/accident-hotspots-2025.json")', 'fetch("http://127.0.0.1:8000/api/statistics/hotspots")'),
  ("fetch('./data/accident-hotspots-2025.json')", "fetch('http://127.0.0.1:8000/api/statistics/hotspots')"),
]


NATIONAL_DONUT_SCRIPT = '\n  // 65세 이상 사망자 상태별 도넛: 17번 CSV(API)로 기존 입체 도넛 모양을 그대로 다시 그려.\n  // 보행 중 조각은 138° 방향으로 앞(아래)쪽에 띄우고(중심 115,84 · 두께 21),\n  // 나머지는 그 끝에서 시계 방향으로 이륜차 → 승용차 → 자전거 → 그 외 순서야(중심 126,86 · 두께 14).\n  function buildDonutSvg(values) {\n    const OUTER = [104, 73], INNER = [42, 30];\n    const MAIN = [126, 86], FRONT = [115, 84];\n    const names = ["보행 중", "이륜차", "승용차", "자전거", "그 외"];\n    // 조각 이름표 위치: 조각 가운데 각도에서 약간 비켜 놓은 값(원본 도넛을 따라 맞춘 값)\n    const labelFit = [null, [0.52, 6.4], [0.584, -0.7], [0.618, 0.7], [0.458, -8.2]];\n    const total = values.reduce((sum, value) => sum + value, 0);\n    const span = values.map((value) => value / total * 360);\n    const rad = (degree) => degree * Math.PI / 180;\n    const fix = (value) => value.toFixed(2);\n    const point = ([cx, cy], [rx, ry], degree) => [cx + rx * Math.cos(rad(degree)), cy + ry * Math.sin(rad(degree))];\n    const at = ([x, y]) => `${fix(x)} ${fix(y)}`;\n    const down = ([x, y], depth) => [x, y + depth];\n    const large = (from, to) => (to - from > 180 ? 1 : 0);\n\n    const frontStart = 138 - span[0] / 2, frontEnd = 138 + span[0] / 2;\n    const slices = [{ start: frontStart, end: frontEnd, center: FRONT, depth: 21 }];\n    let angle = frontEnd;\n    for (let index = 1; index < 5; index += 1) {\n      slices.push({ start: angle, end: angle + span[index], center: MAIN, depth: 14 });\n      angle += span[index];\n    }\n\n    const surface = (slice, number) => {\n      const a = point(slice.center, OUTER, slice.start), b = point(slice.center, OUTER, slice.end);\n      const c = point(slice.center, INNER, slice.end), d = point(slice.center, INNER, slice.start);\n      const flag = large(slice.start, slice.end);\n      return `<path d="M ${at(a)} A 104 73 0 ${flag} 1 ${at(b)} L ${at(c)} A 42 30 0 ${flag} 0 ${at(d)} Z" fill="var(--slice-${number})" class="national-donut-surface" stroke="var(--edge-${number})"/>`;\n    };\n    // 벽면: 안쪽 벽은 위쪽 반(180~360°), 바깥 벽은 아래쪽 반(0~180° = 360~540°)만 보여.\n    const wall = (slice, number, radii, from, to) => {\n      const p = point(slice.center, radii, from), q = point(slice.center, radii, to);\n      const [rx, ry] = radii;\n      return `<path d="M ${at(p)} A ${rx} ${ry} 0 0 1 ${at(q)} L ${at(down(q, slice.depth))} A ${rx} ${ry} 0 0 0 ${at(down(p, slice.depth))} Z" fill="var(--side-${number})"/>`;\n    };\n    const radial = (slice, number, degree) => {\n      const outer = point(slice.center, OUTER, degree), inner = point(slice.center, INNER, degree);\n      return `<path d="M ${at(outer)} L ${at(inner)} L ${at(down(inner, slice.depth))} L ${at(down(outer, slice.depth))} Z" fill="var(--side-${number})"/>`;\n    };\n\n    const parts = [];\n    for (let index = 1; index < 5; index += 1) {\n      const slice = slices[index], number = index + 1;\n      const innerFrom = Math.max(slice.start, 180), innerTo = Math.min(slice.end, 360);\n      if (innerTo - innerFrom > 1e-9) parts.push(wall(slice, number, INNER, innerFrom, innerTo));\n      const outerFrom = Math.max(slice.start, 360), outerTo = Math.min(slice.end, 540);\n      if (outerTo - outerFrom > 1e-9) parts.push(wall(slice, number, OUTER, outerFrom, outerTo));\n    }\n    for (let index = 1; index < 5; index += 1) parts.push(surface(slices[index], index + 1));\n\n    const front = slices[0];\n    if (front.end > 180) parts.push(wall(front, 1, INNER, 180, front.end));\n    if (front.start < 180) parts.push(wall(front, 1, OUTER, front.start, 180));\n    parts.push(radial(front, 1, front.start), radial(front, 1, front.end), surface(front, 1));\n\n    names.forEach((name, index) => {\n      const count = `${values[index].toLocaleString("ko-KR")}명`;\n      if (index === 0) {\n        const x = FRONT[0] + 73 * Math.cos(rad(front.start + 33.9));\n        parts.push(`<text class="national-slice-label national-slice-label-pedestrian" transform="translate(-25 -5)" x="${fix(x)}" y="133.05" style="--label-size: 11px"><tspan x="${fix(x)}">${name}</tspan><tspan x="${fix(x)}" dy="11">${count}</tspan></text>`);\n        return;\n      }\n      const [fraction, shift] = labelFit[index];\n      const middle = (slices[index].start + slices[index].end) / 2 + shift;\n      const [x, y] = point(MAIN, [42 + fraction * 62, 30 + fraction * 43], middle);\n      parts.push(`<text class="national-slice-label" x="${fix(x)}" y="${fix(y)}" style="--label-size: 9.5px"><tspan x="${fix(x)}">${name}</tspan><tspan x="${fix(x)}" dy="11">${count}</tspan></text>`);\n    });\n    parts.push(`<text class="national-donut-total" x="126" y="99">${total.toLocaleString("ko-KR")}<tspan>명</tspan></text>`);\n    return parts.join("");\n  }\n\n  async function loadNationalDonuts() {\n    try {\n      const response = await fetch("http://127.0.0.1:8000/api/traffic/national-deaths");\n\n      if (!response.ok) {\n        throw new Error(`전국 사망자 API 응답 오류: ${response.status}`);\n      }\n\n      const data = await response.json();\n      const card = document.querySelector("#national-status")?.closest("article");\n      const container = card && card.querySelector(".national-donuts");\n      const note = card && card.querySelector(".national-note");\n      const years = Array.isArray(data.years) ? data.years.filter((row) => row.elderly_by_mode) : [];\n\n      if (!container || !note || years.length === 0) {\n        throw new Error("상태별 도넛 자리나 API 값을 확인해 줘.");\n      }\n\n      const order = ["pedestrian", "two_wheeler", "car", "bicycle", "other"];\n      const labels = ["보행 중", "이륜차 승차 중", "승용차 승차 중", "자전거 승차 중", "그 외(차감)"];\n      const kept = new Set();\n\n      for (const row of years) {\n        const values = order.map((key) => row.elderly_by_mode[key]);\n        const total = values.reduce((sum, value) => sum + value, 0);\n        let figure = container.querySelector(`#national-donut-${row.year}`)?.closest("figure");\n\n        if (!figure) {\n          figure = document.createElement("figure");\n          figure.className = "national-donut chart-entered";\n          figure.setAttribute("aria-labelledby", `national-donut-${row.year}`);\n          figure.innerHTML = `<figcaption id="national-donut-${row.year}">${row.year}년</figcaption><svg class="national-donut-shape" viewBox="0 0 246 184" aria-hidden="true"></svg><p class="oecd-sr"></p><ul class="oecd-sr" role="list"></ul>`;\n          container.append(figure);\n        }\n\n        figure.querySelector("svg").innerHTML = buildDonutSvg(values);\n        figure.querySelector("p.oecd-sr").textContent = `65세 이상 사망자 합계 ${total.toLocaleString("ko-KR")}명`;\n        figure.querySelector("ul.oecd-sr").innerHTML = values\n          .map((value, index) => `<li>${labels[index]} ${value.toLocaleString("ko-KR")}명 (${(value / total * 100).toFixed(1)}%)</li>`)\n          .join("");\n        kept.add(`national-donut-${row.year}`);\n      }\n\n      for (const figure of container.querySelectorAll("figure.national-donut")) {\n        if (!kept.has(figure.getAttribute("aria-labelledby"))) figure.remove();\n      }\n\n      const walkingLargest = years.every((row) => {\n        const mode = row.elderly_by_mode;\n        return mode.pedestrian > Math.max(mode.two_wheeler, mode.car, mode.bicycle, mode.other);\n      });\n      note.textContent = walkingLargest\n        ? `단위 명 · 보행 중 사망이 ${years.length}년 연속 가장 많았습니다.`\n        : "단위 명";\n\n      console.info("65세 이상 사망자 상태 도넛 API 연결 완료", years.length);\n    } catch (error) {\n      console.error("65세 이상 사망자 상태 도넛을 불러오지 못했어.", error);\n    }\n  }\n\n  loadNationalDonuts();\n'


SCHOOL_LEGEND_REPLACEMENTS = [('    control.textContent = "어린이보호구역 " + markers.length.toLocaleString("ko-KR") + "곳";\n    control.title = "전국어린이보호구역표준데이터의 서울 시설 기록 · 자료 기준일 2019~2026년";\n', '    // 버튼 숫자는 공식 지정 수, 지도 핀 수는 표준데이터 서울 기록 수라서 서로 달라.\n    const overview = await readProtectionApi("/api/statistics/zone-overview").catch(() => null);\n    const pinCount = markers.length.toLocaleString("ko-KR");\n    if (overview) {\n      const date = overview.child_zone_date;\n      control.textContent = "어린이보호구역 " + overview.child.zones.toLocaleString("ko-KR") + "곳";\n      control.title = date.slice(0, 4) + "년 " + Number(date.slice(5, 7)) + "월 말 서울 지정 현황 · 지도 핀은 전국어린이보호구역표준데이터의 서울 시설 기록 " + pinCount + "건 기준 · 자료 기준일 2019~2026년";\n    } else {\n      control.textContent = "어린이보호구역 " + pinCount + "곳";\n      control.title = "전국어린이보호구역표준데이터의 서울 시설 기록 · 자료 기준일 2019~2026년";\n    }\n')]


ZONE_BUDGET_SCRIPT = '\n  async function loadZoneBudget() {\n    try {\n      const response = await fetch("http://127.0.0.1:8000/api/budget/zone-improvement");\n\n      if (!response.ok) {\n        throw new Error(`보호구역 개선 예산 API 응답 오류: ${response.status}`);\n      }\n\n      const data = await response.json();\n      const rows = document.querySelectorAll("#zone-budget .policy-law-table tbody tr");\n\n      if (rows.length !== 4) {\n        throw new Error("보호구역 개선 예산 표를 확인해 줘.");\n      }\n\n      // 예산서는 천원 단위라 10만 천원 = 1억 원이야. 1곳당 환산액은 서버가 만 원 단위로 계산해 줘.\n      const billion = (thousandWon) => `${(thousandWon / 100000).toFixed(2)}억 원`;\n      const number = (value) => value.toLocaleString("ko-KR");\n      const cells = (row) => row.querySelectorAll("td");\n      const lines = [\n        [data.child, "2025", "곳", ""],\n        [data.child, "2026", "곳", ""],\n        [data.elderly_disabled, "2025", "곳 (노인)", " 이하"],\n        [data.elderly_disabled, "2026", "곳 (노인)", " 이하"],\n      ];\n\n      lines.forEach(([project, year, zoneSuffix, limit], index) => {\n        const td = cells(rows[index]);\n        td[1].textContent = billion(project[`budget_${year}`]);\n        td[2].textContent = `${number(project[`zones_${year}`])}${zoneSuffix}`;\n        td[3].textContent = `약 ${number(project[`per_zone_${year}_man_won`])}만 원${limit}`;\n      });\n\n      console.info("보호구역 개선 예산 API 연결 완료", 4);\n    } catch (error) {\n      console.error("보호구역 개선 예산을 불러오지 못했어.", error);\n    }\n  }\n\n  loadZoneBudget();\n'


CHILD_CAMERA_SCRIPT = '\n  async function loadChildCameraEffect() {\n    try {\n      const response = await fetch("http://127.0.0.1:8000/api/traffic/child-camera-effect");\n\n      if (!response.ok) {\n        throw new Error(`어린이 무인단속카메라 전후 API 응답 오류: ${response.status}`);\n      }\n\n      const data = await response.json();\n      const section = document.querySelector("#policy-school-zones")?.closest("section");\n      const caption = section && section.querySelector(".audit-chart-caption");\n      const columns = section ? section.querySelectorAll(".school-study-bars > div") : [];\n\n      if (!caption || columns.length !== 2) {\n        throw new Error("어린이 무인단속카메라 전후 막대를 확인해 줘.");\n      }\n\n      // 막대 높이는 기존 화면처럼 사고 1건당 3px이야.\n      [["설치 전", data.before], ["설치 후", data.after]].forEach(([label, group], index) => {\n        columns[index].querySelector("dt").innerHTML = `${label}<br>${group.period}년`;\n        columns[index].querySelector("strong").textContent = `${group.accidents}건`;\n        columns[index].querySelector("span").style.setProperty("--bar-height", `${group.accidents * 3}px`);\n      });\n      caption.textContent = `어린이 보행사고 ${data.before.accidents}건 → ${data.after.accidents}건 · ${data.accidents_reduction_percent}% 감소`;\n\n      console.info("어린이보호구역 카메라 전후 API 연결 완료", 2);\n    } catch (error) {\n      console.error("어린이 무인단속카메라 전후 비교를 불러오지 못했어.", error);\n    }\n  }\n\n  loadChildCameraEffect();\n'


ZONE_OVERVIEW_SCRIPT = '\n  async function loadZoneOverview() {\n    try {\n      const response = await fetch("http://127.0.0.1:8000/api/statistics/zone-overview");\n\n      if (!response.ok) {\n        throw new Error(`보호구역 현황 API 응답 오류: ${response.status}`);\n      }\n\n      const data = await response.json();\n      const chart = document.querySelector(".school-zone-overview .zone-density");\n      const source = document.querySelector(".school-zone-overview .compare-chart > .policy-source");\n      const bars = chart ? chart.querySelectorAll(":scope > div[style*=\'--zone-width\']") : [];\n      const values = chart ? chart.querySelectorAll(".zone-density-value") : [];\n      const people = chart ? chart.querySelectorAll(".zone-density-people strong") : [];\n\n      if (!source || bars.length !== 2 || values.length !== 2 || people.length !== 2) {\n        throw new Error("보호구역 현황 막대나 문구를 확인해 줘.");\n      }\n\n      // 축이 0~30곳이라 막대 너비는 30곳 대비 비율이야.\n      [data.child, data.elderly].forEach((group, index) => {\n        bars[index].style.setProperty("--zone-width", `${(group.zones_per_10k / 30 * 100).toFixed(4)}%`);\n        values[index].textContent = `${group.zones_per_10k.toFixed(2)}곳`;\n        people[index].textContent = `약 ${group.people_per_zone.toLocaleString("ko-KR")}명`;\n      });\n      source.textContent = `어린이 ${data.child.population.toLocaleString("ko-KR")}명 · ${data.child.zones.toLocaleString("ko-KR")}곳(${data.child_zone_date.slice(0, 4)}년) | 노인 ${data.elderly.population.toLocaleString("ko-KR")}명 · ${data.elderly.zones.toLocaleString("ko-KR")}곳(${data.elderly_year}년)`;\n\n      console.info("서울 보호구역 현황 API 연결 완료", 2);\n    } catch (error) {\n      console.error("서울 보호구역 현황을 불러오지 못했어.", error);\n    }\n  }\n\n  loadZoneOverview();\n'


PROTECTION_MAP_REPLACEMENTS = [('function hasProtectionCoordinates(row) {', 'async function readProtectionApi(path) {\n  const response = await fetch("http://127.0.0.1:8000" + path);\n  if (!response.ok) throw new Error("API HTTP " + response.status);\n  return response.json();\n}\n\nfunction hasProtectionCoordinates(row) {'), ('    const rows = await readProtectionCsv("./data/09_어린이보호구역_서울.csv");\n', '    const rows = (await readProtectionApi("/api/school-zones")).zones.map(zone => ({\n      시설명: zone.name, 자치구명: zone.district, 도로명주소: zone.road_address ?? "",\n      지번주소: zone.lot_address ?? "", 위도: zone.lat, 경도: zone.lng, 데이터기준일: zone.data_date ?? ""\n    }));\n'), ('    const [master, rows] = await Promise.all([\n      readProtectionCsv("./data/04_보호구역_마스터.csv"),\n      readProtectionCsv("./data/05_보호구역_경계.csv")\n    ]);\n    const facilities = [...new Map(\n      master.filter(row => row.명단2025 === "1").map(row => [row.시설ID, row])\n    ).values()];\n    const boundaries = new Map();\n    const matchRank = row => row.명단매칭방식?.includes("검수필요") ? 0 :\n      row.명단매칭방식 === "주소+시설명" ? 2 : 1;\n    for (const row of rows.filter(hasProtectionCoordinates)) {\n      const previous = boundaries.get(row.시설ID);\n      if (!previous || matchRank(row) > matchRank(previous) ||\n          (matchRank(row) === matchRank(previous) && row.데이터기준일 > previous.데이터기준일)) {\n        boundaries.set(row.시설ID, row);\n      }\n    }\n', '    const zoneData = await readProtectionApi("/api/protection-zones");\n    const facilities = zoneData.facilities.map(zone => ({\n      시설ID: zone.id, 시설명: zone.name, 자치구명: zone.district, 위치: zone.address,\n      위도: zone.lat, 경도: zone.lng, 데이터기준일: zone.data_date ?? "",\n      명단매칭방식: zone.match_method ?? "", 위치안내: zone.note ?? ""\n    }));\n    const missing = zoneData.unlocated.map(zone => ({\n      시설ID: zone.id, 시설명: zone.name, 자치구명: zone.district, 위치: zone.address\n    }));\n'), ('    const missing = [];\n    for (const facility of facilities) {\n      const location = boundaries.get(facility.시설ID) ||\n        (facility.시설ID === "Z186" ? {\n          위도: 37.580216,\n          경도: 127.042424,\n          위치안내: "시장 대표 위치 · 보호구역 경계와 다를 수 있어"\n        } : null);\n      if (location) addMarker(facility, location);\n      else missing.push(facility);\n    }\n', '    for (const facility of facilities) addMarker(facility, facility);\n'), ('    status.textContent = "노인보호구역 " + facilities.length + "곳";\n', '    status.textContent = "노인보호구역 " + zoneData.total + "곳";\n'), ('"2025년 명단 기준 · 지도에 표시할 수 있는 시설 " + markers.length + "/" + facilities.length + "곳";', '"2025년 명단 기준 · 지도에 표시할 수 있는 시설 " + markers.length + "/" + zoneData.total + "곳";'), ("      readProtectionCsv('./data/05_보호구역_경계.csv'),\n", "      readProtectionApi('/api/protection-zones/boundaries').then(data =>\n        data.zones.map(zone => ({ 시설ID: zone.facility_id, 경계WKT: zone.wkt }))),\n")]


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


def step_zone_budget(text):
    """예전 버전(어린이 구역 수 미연결)을 새 버전으로 바꾼다."""
    old_start = text.find("\n  async function loadZoneBudget() {")
    if old_start != -1 and "per_zone_${year}_man_won" not in text:
        old_end_marker = "\n  loadZoneBudget();\n"
        old_end = text.find(old_end_marker, old_start)
        if old_end == -1:
            return text, "못 찾음(예전 예산 스크립트 끝)"
        text = text[:old_start].rstrip("\n") + "\n" + text[old_end + len(old_end_marker):]
    return append_script(
        text, "per_zone_${year}_man_won", ZONE_BUDGET_SCRIPT,
        ['id="zone-budget"', 'zone-budget-table-title'], "",
    )


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
    (
        "65세 이상 인구 추이",
        lambda t: append_script(
            t, "loadElderlyPopulation", POPULATION_SCRIPT,
            ['class="national-population"', 'class="population-value"'], "",
        ),
    ),
    (
        "노인보호구역 지정 전후",
        lambda t: append_script(
            t, "loadZoneBeforeAfter", ZONE_BEFORE_AFTER_SCRIPT,
            ['id="zone-before-after"', 'class="risk-change-table"'], "",
        ),
    ),
    (
        "동대문·도봉 4년 비교",
        lambda t: append_script(
            t, "loadDistrictComparison", COMPARISON_SCRIPT,
            ['id="district-comparison"', 'data-risk-plot="rate"'], "",
        ),
    ),
    (
        "사고다발지역 검토 표·막대",
        lambda t: append_script(
            t, "loadHotspotReview", HOTSPOT_REVIEW_SCRIPT,
            ['id="zone-review"', 'class="review-chart"', 'review-candidates'], "",
        ),
    ),
    (
        "지도의 사고다발지역 점",
        lambda t: replace_exact(t, 'fetch("http://127.0.0.1:8000/api/statistics/hotspots")', HOTSPOT_MAP_REPLACEMENTS),
    ),
    (
        "지도의 보호구역·어린이보호구역",
        lambda t: replace_exact(t, "readProtectionApi", PROTECTION_MAP_REPLACEMENTS),
    ),
    (
        "서울 보호구역 현황",
        lambda t: append_script(
            t, "loadZoneOverview", ZONE_OVERVIEW_SCRIPT,
            ['class="zone-density"', 'school-zone-overview'], "",
        ),
    ),
    (
        "어린이 카메라 설치 전후",
        lambda t: append_script(
            t, "loadChildCameraEffect", CHILD_CAMERA_SCRIPT,
            ['id="policy-school-zones"', 'school-study-bars'], "",
        ),
    ),
    (
        "보호구역 개선 예산",
        step_zone_budget,
    ),
    (
        "어린이보호구역 버튼 숫자",
        lambda t: replace_exact(t, "pinCount", SCHOOL_LEGEND_REPLACEMENTS),
    ),
    (
        "65세 이상 사망자 상태 도넛",
        lambda t: append_script(
            t, "loadNationalDonuts", NATIONAL_DONUT_SCRIPT,
            ['id="national-status"', 'class="national-donuts"'], "",
        ),
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

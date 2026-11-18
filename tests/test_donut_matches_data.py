"""화면의 '65세 이상 사망자의 사고 당시 상태' 도넛 숫자가 17번 CSV와 같은지 확인한다."""

import re
from pathlib import Path

import pandas as pd

from app.services.data_files import NATIONAL_DEATHS_FILE

HTML = Path(__file__).resolve().parents[1] / "seoul-traffic-demo.html"
MODES = {
    "보행 중": "65세이상_보행중",
    "이륜차": "65세이상_이륜차",
    "승용차": "65세이상_승용차",
    "자전거": "65세이상_자전거",
    "그 외": "65세이상_그외(차감)",
}


def donut_figures():
    html = HTML.read_text(encoding="utf-8")
    return re.findall(r'<figure class="national-donut".*?</figure>', html, re.S)


def test_page_donuts_equal_csv(real_data_dir):
    data = pd.read_csv(real_data_dir / NATIONAL_DEATHS_FILE, encoding="utf-8-sig").set_index("연도")
    figures = donut_figures()
    drawn_years = []
    for figure in figures:
        year = int(re.search(r"(\d{4})년</figcaption>", figure).group(1))
        drawn_years.append(year)
        row = data.loc[year]
        total = int(re.search(r'national-donut-total"[^>]*>([\d,]+)', figure).group(1).replace(",", ""))
        labels = {
            name: int(value.replace(",", ""))
            for name, value in re.findall(
                r'<tspan x="[\d.]+">([^<]+)</tspan><tspan x="[\d.]+" dy="[\d.]+">([\d,]+)명</tspan>', figure
            )
        }
        assert total == row["65세이상_사망자수"], year
        assert labels == {name: int(row[column]) for name, column in MODES.items()}, year
        # 스크린리더용 목록의 비율도 같아야 한다.
        for name, value, percent in re.findall(r"<li>(.+?) ([\d,]+)명 \(([\d.]+)%\)</li>", figure):
            count = int(value.replace(",", ""))
            assert percent == f"{count / total * 100:.1f}", (year, name)

    # 화면은 상태별 구분이 있는 연도만 그린다.
    with_modes = data[data[list(MODES.values())].notna().all(axis=1)].index.tolist()
    assert drawn_years == with_modes


def test_walking_is_largest_every_drawn_year(real_data_dir):
    """화면 문구 '보행 중 사망이 N년 연속 가장 많았습니다'를 데이터로 확인한다."""

    data = pd.read_csv(real_data_dir / NATIONAL_DEATHS_FILE, encoding="utf-8-sig")
    drawn = data[data[list(MODES.values())].notna().all(axis=1)]
    for _, row in drawn.iterrows():
        others = [row[column] for name, column in MODES.items() if name != "보행 중"]
        assert row["65세이상_보행중"] > max(others), row["연도"]
    html = HTML.read_text(encoding="utf-8")
    assert f"보행 중 사망이 {len(drawn)}년 연속 가장 많았습니다" in html

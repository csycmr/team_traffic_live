"""노인보호구역 지정 전후 자치구 고령 보행자 사고 비교."""

from pathlib import Path

import pandas as pd

from app.errors import ServiceError
from app.models import ZoneBeforeAfter, ZoneBeforeAfterCase
from app.services.data_files import (
    PANEL_FILE,
    PROTECTION_MASTER_FILE,
    read_csv,
    require_columns,
)

# 패널이 2022~2025년이라 전년도와 이듬해가 모두 있는 지정연도만 비교할 수 있다.
PANEL_COLUMNS = ["자치구명", "사고연도", "고령인구", "고령보행자_사고건수"]
MASTER_COLUMNS = ["자치구명", "지정연도", "명단2025"]


def zone_before_after(data_dir: Path | str | None = None) -> ZoneBeforeAfter:
    """2025년 명단 구역을 자치구·지정연도로 묶고 전년도 → 지정연도 → 이듬해 사고를 비교한다."""

    master = read_csv(PROTECTION_MASTER_FILE, data_dir)
    panel = read_csv(PANEL_FILE, data_dir)
    require_columns(master, PROTECTION_MASTER_FILE, MASTER_COLUMNS)
    require_columns(panel, PANEL_FILE, PANEL_COLUMNS)

    if panel.duplicated(["자치구명", "사고연도"]).any():
        raise ServiceError(f"{PANEL_FILE}에 같은 자치구·연도가 겹쳐 있어.", 500)
    panel = panel.set_index(["자치구명", "사고연도"])
    years = panel.index.get_level_values(1)
    first_year, last_year = int(years.min()), int(years.max())

    listed = master[master["명단2025"].eq(1) & master["지정연도"].notna()]
    groups = (
        listed[listed["지정연도"].between(first_year + 1, last_year - 1)]
        .groupby(["자치구명", "지정연도"])
        .size()
    )

    cases = []
    for (district, year), zones in groups.items():
        year = int(year)
        values = {}
        for key, target in (("before", year - 1), ("at", year), ("after", year + 1)):
            try:
                row = panel.loc[(district, target)]
            except KeyError as error:
                raise ServiceError(f"{district} {target}년 자치구 사고 자료가 없어.", 500) from error
            if row[["고령인구", "고령보행자_사고건수"]].isna().any() or row["고령인구"] <= 0:
                raise ServiceError(f"{district} {target}년 사고·인구 값이 비어 있어.", 500)
            values[key] = (
                int(row["고령보행자_사고건수"]),
                round(float(row["고령보행자_사고건수"] / row["고령인구"] * 10000), 2),
            )
        cases.append(
            ZoneBeforeAfterCase(
                district=district,
                designated_year=year,
                zones=int(zones),
                accidents_before=values["before"][0],
                accidents_at=values["at"][0],
                accidents_after=values["after"][0],
                accidents_change=values["after"][0] - values["before"][0],
                rate_before=values["before"][1],
                rate_at=values["at"][1],
                rate_after=values["after"][1],
            )
        )

    if not cases:
        raise ServiceError("지정 전후를 비교할 사례가 없어.", 500)

    # 지정연도 순, 같은 해에서는 증감이 큰 순서로 보여 준다.
    cases.sort(key=lambda c: (c.designated_year, -c.accidents_change, c.district))
    changes = [c.accidents_change for c in cases]
    return ZoneBeforeAfter(
        districts=len({c.district for c in cases}),
        increased=sum(v > 0 for v in changes),
        decreased=sum(v < 0 for v in changes),
        unchanged=sum(v == 0 for v in changes),
        cases=cases,
    )

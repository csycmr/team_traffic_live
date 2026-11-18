"""전국 65세 이상 주민등록인구(행정안전부 주민등록 인구통계)."""

import re
from pathlib import Path

from app.errors import ServiceError
from app.models import ElderlyPopulation
from app.services.data_files import ELDERLY_POPULATION_FILE, read_csv, require_columns

PERIOD = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def elderly_population(data_dir: Path | str | None = None) -> ElderlyPopulation:
    """기준연월(YYYY-MM)과 65세 이상 인구수를 시간 순서로 돌려준다."""

    data = read_csv(ELDERLY_POPULATION_FILE, data_dir)
    require_columns(data, ELDERLY_POPULATION_FILE, ["기준연월", "65세이상_인구수"])
    if data[["기준연월", "65세이상_인구수"]].isna().any().any():
        raise ServiceError(f"{ELDERLY_POPULATION_FILE}에 비어 있는 값이 있어.", 500)
    if data["기준연월"].duplicated().any():
        raise ServiceError(f"{ELDERLY_POPULATION_FILE}에 같은 기준연월이 겹쳐 있어.", 500)

    points = []
    for _, row in data.iterrows():
        match = PERIOD.match(str(row["기준연월"]).strip())
        if not match:
            raise ServiceError(
                f"기준연월은 YYYY-MM 형식이어야 해: {row['기준연월']}", 500
            )
        points.append(
            {
                "year": int(match.group(1)),
                "month": int(match.group(2)),
                "population": int(row["65세이상_인구수"]),
            }
        )
    points.sort(key=lambda point: (point["year"], point["month"]))
    return ElderlyPopulation(points=points)

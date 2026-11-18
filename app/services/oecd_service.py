"""OECD 고령 교통사고 사망률 순위."""

from pathlib import Path

from app.models import OecdRankings
from app.services.data_files import OECD_FILE, read_csv, require_columns

RATE_COLUMN = "65세이상_인구10만명당_사망자수"
FIRST_YEAR, LAST_YEAR = 2020, 2023


def oecd_rankings(data_dir: Path | str | None = None) -> OecdRankings:
    data = read_csv(OECD_FILE, data_dir)
    require_columns(data, OECD_FILE, ["국가구분", "연도", "국가", "ISO3", RATE_COLUMN])

    members = data.loc[
        data["국가구분"].eq("회원국") & data["연도"].between(FIRST_YEAR, LAST_YEAR)
    ].dropna(subset=[RATE_COLUMN])

    years = []
    for year, group in members.groupby("연도"):
        ranked = group.sort_values(
            [RATE_COLUMN, "ISO3"], ascending=[False, True]
        ).copy()
        ranked["rank"] = ranked[RATE_COLUMN].rank(
            ascending=False, method="min"
        ).astype(int)

        top_ten = ranked.head(10).rename(
            columns={"국가": "country", "ISO3": "iso3", RATE_COLUMN: "rate"}
        )
        years.append({
            "year": int(year),
            "country_count": len(ranked),
            "countries": top_ten[["country", "iso3", "rate", "rank"]].to_dict(
                orient="records"
            ),
        })

    return OecdRankings(years=years)

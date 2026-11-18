from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5001"],
    allow_methods=["GET"],
)

CSV_PATH = Path(__file__).resolve().parent / "data" / "13_OECD_고령지표_wide.csv"
RATE_COLUMN = "65세이상_인구10만명당_사망자수"


@app.get("/api/oecd/rankings")
def get_oecd_rankings():
    data = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    members = data.loc[
        data["국가구분"].eq("회원국") & data["연도"].between(2020, 2023)
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
            "countries": top_ten[["country", "iso3", "rate", "rank"]]
            .to_dict(orient="records"),
        })

    return {"years": years}

ACCIDENT_TREND_CSV = (
    Path(__file__).resolve().parent
    / "data"
    / "15_전국서울_교통사고_추이.csv"
)


@app.get("/api/traffic/accident-trend")
def get_accident_trend():
    data = pd.read_csv(ACCIDENT_TREND_CSV, encoding="utf-8-sig")
    data = data.sort_values("year")
    return {"years": data.to_dict(orient="records")}
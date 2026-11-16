"""
13_OECD_교통사고_2019-2023.csv 전처리·정제 스크립트

원본: 한국도로교통공단 《OECD 회원국 교통사고 비교》 2021~2025년판에서 옮긴 long 형식 표
출력 (기본 data/):
  13_OECD_전판본_정제.csv      모든 판본의 수치 행을 정제한 것 (추적용, 원본 행 1:1)
  13_OECD_정제.csv             국가·연도·지표·연령층·사고시상태별 1행 (최신 판본 우선)
  13_OECD_고령지표_wide.csv    2019~2023년 국가×연도 고령(65세 이상) 핵심 지표 + 순위
  13_OECD_부록_교통안전전략.csv  부록(IRTAD 국가별 추진전략·목표) 텍스트

사용: python3 scripts/clean_oecd_13.py [입력csv] [출력폴더]
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/13_OECD_교통사고_2019-2023.csv")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data")
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 국가 사전
# (영문명, ISO3, 국가구분)
COUNTRY = {
    "호주": ("Australia", "AUS"), "오스트리아": ("Austria", "AUT"), "벨기에": ("Belgium", "BEL"),
    "캐나다": ("Canada", "CAN"), "칠레": ("Chile", "CHL"), "콜롬비아": ("Colombia", "COL"),
    "코스타리카": ("Costa Rica", "CRI"), "체코": ("Czechia", "CZE"), "덴마크": ("Denmark", "DNK"),
    "에스토니아": ("Estonia", "EST"), "핀란드": ("Finland", "FIN"), "프랑스": ("France", "FRA"),
    "독일": ("Germany", "DEU"), "그리스": ("Greece", "GRC"), "헝가리": ("Hungary", "HUN"),
    "아이슬란드": ("Iceland", "ISL"), "아일랜드": ("Ireland", "IRL"), "이스라엘": ("Israel", "ISR"),
    "이탈리아": ("Italy", "ITA"), "일본": ("Japan", "JPN"), "대한민국": ("Korea", "KOR"),
    "라트비아": ("Latvia", "LVA"), "리투아니아": ("Lithuania", "LTU"), "룩셈부르크": ("Luxembourg", "LUX"),
    "멕시코": ("Mexico", "MEX"), "네덜란드": ("Netherlands", "NLD"), "뉴질랜드": ("New Zealand", "NZL"),
    "노르웨이": ("Norway", "NOR"), "폴란드": ("Poland", "POL"), "포르투갈": ("Portugal", "PRT"),
    "슬로바키아": ("Slovakia", "SVK"), "슬로베니아": ("Slovenia", "SVN"), "스페인": ("Spain", "ESP"),
    "스웨덴": ("Sweden", "SWE"), "스위스": ("Switzerland", "CHE"), "튀르키예": ("Türkiye", "TUR"),
    "영국": ("United Kingdom", "GBR"), "미국": ("United States", "USA"),
    # 부록에만 나오는 비회원국
    "아르헨티나": ("Argentina", "ARG"), "캄보디아": ("Cambodia", "KHM"), "말레이시아": ("Malaysia", "MYS"),
    "모로코": ("Morocco", "MAR"), "나이지리아": ("Nigeria", "NGA"), "세르비아": ("Serbia", "SRB"),
    "OECD 평균": ("OECD average", "OECD"),
}
NON_MEMBER = {"아르헨티나", "캄보디아", "말레이시아", "모로코", "나이지리아", "세르비아"}
COUNTRY_FIX = {"일독": "독일", "OECD 회원국 평균": "OECD 평균"}

AGE_NORM = {"15-24세": "15~24세", "25-64세": "25~64세"}

# ---------------------------------------------------------------- 읽기·공통 정리
raw = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str)
n_raw = len(raw)
raw["원본행번호"] = np.arange(2, n_raw + 2)  # 엑셀 기준 행 번호(헤더=1)
for c in raw.columns:
    if raw[c].dtype == object or str(raw[c].dtype).startswith("str"):
        raw[c] = raw[c].str.strip().str.replace(r"\s+", " ", regex=True)

raw["국가_원문"] = raw["국가"]
raw["국가"] = raw["국가"].replace(COUNTRY_FIX)
unknown = set(raw["국가"]) - set(COUNTRY)
assert not unknown, f"사전에 없는 국가: {unknown}"
raw["국가_영문"] = raw["국가"].map(lambda k: COUNTRY[k][0])
raw["ISO3"] = raw["국가"].map(lambda k: COUNTRY[k][1])
raw["국가구분"] = np.select(
    [raw["국가"].eq("OECD 평균"), raw["국가"].isin(NON_MEMBER)],
    ["평균", "비회원국"], default="회원국",
)

# ---------------------------------------------------------------- 부록 분리
app = raw[raw["자료구분"] == "부록"].copy()
app["내용"] = app["원문표기"].where(app["자료상태"] != "자료 없음")
app = app[["보고서판본", "국가", "국가_영문", "ISO3", "국가구분", "지표", "내용", "자료상태", "인쇄쪽", "PDF쪽", "출처", "원본행번호"]]
app = app.rename(columns={"지표": "항목"})
app.loc[app["국가"].eq("독일") & app["보고서판본"].eq("2021"), "비고"] = "원문 국가명 '일독'을 독일로 정정"
app.to_csv(OUT / "13_OECD_부록_교통안전전략.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 수치 표
d = raw[raw["자료구분"] != "부록"].copy()

# 1) 원문 확인 필요 3건 처리
flags = pd.Series([[] for _ in range(len(d))], index=d.index)
def add_flag(mask, text):
    for i in d.index[mask]:
        flags.at[i].append(text)

m_nor = (d["자료상태"] == "원문 확인 필요") & d["국가"].eq("노르웨이") & d["원문표기"].eq("20.")
d.loc[m_nor, "수치"] = "2.0"   # 같은 판본 그림 I-8·본문 20쪽 = 2.0
add_flag(m_nor, "원문 오식(20.) → 그림 I-8 값 2.0으로 정정")
m_fra = (d["자료상태"] == "원문 확인 필요") & d["원문표기"].eq("-3.")
d.loc[m_fra, "수치"] = "-3"
add_flag(m_fra, "원문 '-3.' 표기 — 소수 자리 불확실")
m_dot = (d["자료상태"] == "원문 확인 필요") & d["원문표기"].eq(".")
add_flag(m_dot, "원문 '.' 표기 — 값 없음 처리")

# 2) 값
d["값"] = pd.to_numeric(d["수치"], errors="coerce")
d["자료없음"] = d["값"].isna()

# 3) 연도: 개별자료연도가 있으면 그것이 실제 자료연도
d["표기연도"] = pd.to_numeric(d["표기연도"]).astype("Int64")
d["개별자료연도"] = pd.to_numeric(d["개별자료연도"]).astype("Int64")
d["연도"] = d["개별자료연도"].fillna(d["표기연도"]).astype("Int64")
add_flag(d["개별자료연도"].notna(), "이전 연도 자료 사용(연도 명시)")
add_flag(d["비고"].fillna("").str.contains("이전 연도 자료를 사용했으며 개별 연도 미표기"),
         "일부 국가 이전 연도 자료 가능(연도 미표기)")
add_flag(d["비고"].fillna("").str.contains("정정|입력했으며 인용 전 확인"), "원문 연도 머리글 오류 정정")
add_flag(d["비고"].fillna("").str.contains("사망사고 건수만 집계"), "사고건수=사망사고만 집계")
add_flag(d["비고"].fillna("").str.contains("00%"), "원문 '00%' 표기")

# 4) 원문 각주 기호 분리 (예: "1,027,545 a")
d["원문각주"] = d["원문표기"].str.extract(r"\s([a-z](?:,\s?[a-z])*)$")[0]

# 5) 연령층·사고시상태: 그림·본문(OECD 평균)은 지표명에서 파싱, 공란은 '전체'
def parse_age(s):
    m = re.search(r"(14세 이하|15[-~]24세|25[-~]64세|65세 이상)", s)
    return AGE_NORM.get(m.group(1), m.group(1)) if m else None
def parse_mode(s):
    m = re.search(r"(보행 중|승용차 승차 중|이륜차 승차 중|자전거 승차 중)", s)
    return m.group(1) if m else None

fig = d["자료구분"].eq("그림·본문")
d.loc[fig & d["연령층"].isna(), "연령층"] = d.loc[fig, "지표"].map(parse_age)
d.loc[fig & d["사고시상태"].isna(), "사고시상태"] = d.loc[fig, "지표"].map(parse_mode)
d["연령층"] = d["연령층"].replace(AGE_NORM).fillna("전체")
d["사고시상태"] = d["사고시상태"].fillna("전체")

# 6) 지표 표준화: 측정대상 + 기준(단위) → 표준 지표명
def base_measure(r):
    s = r["지표"]
    if r["자료구분"] == "그림·본문":
        if "구성비" in s: return "사망자수 구성비"
        if "치사율" in s: return "치사율"
        if "증감률" in s: return "사고건수 증감률" if "사고건수" in s else "사망자수 증감률"
        if "자동차 보유대수" in s: return "자동차 보유대수"
        if "도로연장" in s: return "도로연장"
        if "도로밀도" in s: return "도로밀도"
        if "사고건수" in s: return "사고건수"
        return "사망자수"
    return {
        "교통사고 사망자수": "사망자수", "교통사고건수": "사고건수", "교통사고 부상자수": "부상자수",
        "교통사고 치사율": "치사율",
        "교통사고건수 전년대비 증감률": "사고건수 증감률",
        "교통사고 사망자수 전년대비 증감률": "사망자수 증감률",
        "교통사고 부상자수 전년대비 증감률": "부상자수 증감률",
    }.get(s, s)  # 교통여건(인구·자동차 등록대수 등)은 그대로

BASIS = {
    "명/인구 10만 명": "인구 10만 명당", "건/인구 10만 명": "인구 10만 명당",
    "명/해당 인구 10만 명": "해당 연령 인구 10만 명당",
    "명/자동차 1만 대": "자동차 1만 대당", "건/자동차 1만 대": "자동차 1만 대당",
    "명/10억 주행 km": "10억 주행km당", "건/10억 주행 km": "10억 주행km당",
    "대/인구 100명": "인구 100명당", "km/인구 100명": "인구 100명당",
}
d["측정대상"] = d.apply(base_measure, axis=1)
d["기준"] = d["단위"].map(BASIS).fillna("")
d.loc[d["측정대상"].eq("사망자수 구성비") & d["기준"].eq(""), "기준"] = ""
d["지표_표준"] = (d["기준"] + " " + d["측정대상"]).str.strip()
d["단위"] = d["단위"].replace({"원문 지표": "지수(원문)"})

# 그림·본문 구성비: 연령·상태는 '분자' 조건이므로 지표명에 그대로 남겨둔다
# (예: 65세 이상 사망자수 구성비 = 전체 사망자 중 65세 이상 비중)

d["품질플래그"] = flags.map(lambda x: "; ".join(dict.fromkeys(x)))
d["판본"] = d["보고서판본"].astype(int)

cols_full = ["국가", "국가_영문", "ISO3", "국가구분", "연도", "표기연도", "지표_표준", "측정대상", "기준",
             "연령층", "사고시상태", "단위", "값", "자료없음", "판본", "자료구분", "자료번호", "자료명",
             "인쇄쪽", "PDF쪽", "지표", "원문표기", "원문각주", "자료상태", "품질플래그", "비고", "출처",
             "국가_원문", "원본행번호"]
full = d[cols_full].rename(columns={"지표": "지표_원문"})
full.to_csv(OUT / "13_OECD_전판본_정제.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 판본 중복 제거
key = ["국가", "연도", "지표_표준", "연령층", "사고시상태", "단위"]
v = full[~full["자료없음"]].copy()
# 같은 판본 안 중복(I-6과 II-1 등)은 값이 모두 같음 → 통계표 우선, 자료번호 순
v["_prio"] = v["자료구분"].map({"통계표": 0, "그림·본문": 1})
v = v.sort_values(key + ["판본", "_prio"], ascending=[True] * len(key) + [False, True])

def summarize(g):
    by_ed = g.drop_duplicates("판본").set_index("판본")["값"].sort_index()
    top = g[g["판본"].eq(g["판본"].max())]
    inner = ""
    if top["값"].nunique() > 1:  # 같은 판본 안에서 표끼리 숫자가 다른 경우
        inner = "같은 판본 표 간 값 상이: " + ", ".join(
            f"{r.자료번호}={r.값:g}" for r in top.drop_duplicates(["자료번호"]).itertuples())
    return pd.Series({
        "수록판본": ",".join(map(str, by_ed.index)),
        "판본간_값상이": by_ed.nunique() > 1,
        "판본별값": "|".join(f"{e}:{x:g}" for e, x in by_ed.items()) if by_ed.nunique() > 1 else "",
        "_inner": inner,
    })

summ = v.groupby(key, sort=False).apply(summarize, include_groups=False).reset_index()
latest = v.drop_duplicates(key, keep="first")
dedup = latest.merge(summ, on=key, how="left")
dedup["품질플래그"] = (dedup["품질플래그"].fillna("") + "; " + dedup.pop("_inner")).str.strip("; ")
cols_dedup = ["국가", "국가_영문", "ISO3", "국가구분", "연도", "지표_표준", "측정대상", "기준",
              "연령층", "사고시상태", "단위", "값", "판본", "자료번호", "자료명", "원문각주",
              "수록판본", "판본간_값상이", "판본별값", "품질플래그", "비고"]
dedup = dedup[cols_dedup].rename(columns={"판본": "채택판본"})
dedup = dedup.sort_values(["국가구분", "국가", "지표_표준", "연령층", "사고시상태", "연도"],
                          key=lambda s: s.map({"회원국": 0, "평균": 1, "비회원국": 2}) if s.name == "국가구분" else s)
dedup.to_csv(OUT / "13_OECD_정제.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 고령 지표 wide (2019~2023)
W = {
    ("사망자수", "전체", "전체"): "전체_사망자수",
    ("인구 10만 명당 사망자수", "전체", "전체"): "전체_인구10만명당_사망자수",
    ("사망자수", "65세 이상", "전체"): "65세이상_사망자수",
    ("해당 연령 인구 10만 명당 사망자수", "65세 이상", "전체"): "65세이상_인구10만명당_사망자수",
    ("사망자수", "65세 이상", "보행 중"): "65세이상_보행중_사망자수",
    ("해당 연령 인구 10만 명당 사망자수", "65세 이상", "보행 중"): "65세이상_인구10만명당_보행중_사망자수",
    ("사망자수", "65세 이상", "승용차 승차 중"): "65세이상_승용차_사망자수",
    ("사망자수", "65세 이상", "이륜차 승차 중"): "65세이상_이륜차_사망자수",
    ("사망자수", "65세 이상", "자전거 승차 중"): "65세이상_자전거_사망자수",
}
x = dedup[dedup["연도"].between(2019, 2023) & dedup["국가구분"].ne("비회원국")].copy()
x["열"] = [W.get(t) for t in zip(x["지표_표준"], x["연령층"], x["사고시상태"])]
x = x[x["열"].notna()]
wide = x.pivot_table(index=["국가", "ISO3", "국가구분", "연도"], columns="열", values="값", aggfunc="first")
wide = wide.reindex(columns=[c for c in W.values() if c in wide.columns]).reset_index()
# 비중의 분모는 65세 이상 값과 같은 표(II-2, 연령층별 사망자수)의 '전체'를 쓴다.
# (I-6 총계와 II-2 합계가 다른 국가가 있어서: 2025년판 캐나다·에스토니아 2023년)
age_tab = full[full["자료번호"].eq("II-2") & ~full["자료없음"]]
den = (age_tab[age_tab["연령층"].eq("전체")]
       .sort_values("판본", ascending=False)
       .drop_duplicates(["국가", "연도"])[["국가", "연도", "값"]]
       .rename(columns={"값": "_den"}))
wide = wide.merge(den, on=["국가", "연도"], how="left")
wide["65세이상_사망자_비중(%)"] = (wide["65세이상_사망자수"] / wide["_den"].fillna(wide["전체_사망자수"]) * 100).round(1)
wide = wide.drop(columns="_den")
wide["65세이상_중_보행사망_비중(%)"] = (wide["65세이상_보행중_사망자수"] / wide["65세이상_사망자수"] * 100).round(1)
mem = wide["국가구분"].eq("회원국")
for col, name in [("65세이상_인구10만명당_보행중_사망자수", "순위_65세이상_보행중_10만명당"),
                  ("65세이상_인구10만명당_사망자수", "순위_65세이상_10만명당")]:
    wide.loc[mem, name] = wide[mem].groupby("연도")[col].rank(ascending=False, method="min")
    wide.loc[mem, name.replace("순위", "비교국수")] = wide[mem].groupby("연도")[col].transform("count")
    wide[name] = wide[name].astype("Int64")
    wide[name.replace("순위", "비교국수")] = wide[name.replace("순위", "비교국수")].astype("Int64")
wide = wide.sort_values(["연도", "국가구분", "국가"])
wide.to_csv(OUT / "13_OECD_고령지표_wide.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 요약
print(f"원본 {n_raw:,}행 = 수치 {len(full):,} + 부록 {len(app):,}")
print(f"전판본 정제: {len(full):,}행 (자료없음 {full['자료없음'].sum():,})")
print(f"중복 제거: {len(dedup):,}행 (판본간 값 상이 {dedup['판본간_값상이'].sum():,})")
print(f"고령 wide: {len(wide):,}행 × {wide.shape[1]}열")

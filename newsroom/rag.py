
"""공식 문서의 확인된 발췌문을 검색하는 최소 RAG 검색기."""


"""공식 문서 검색 및 근거 기반 AI 답변."""

import json
import os
import re

import pandas as pd

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from newsroom.data import dataset_state, load_data
from newsroom.recommendation import fact_sheet

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity



load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent / ".env"
)


from pathlib import Path

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "rag_sources.json"
)




def search_documents(question: str, limit: int = 3) -> list[dict]:
    """공식 문서의 실제 내용과 검색 키워드를 TF-IDF로 비교한다."""

    if not question.strip():
        return []

    documents = json.loads(
        DATA_FILE.read_text(encoding="utf-8")
    )

    if not documents:
        return []

    # 실제 원문 + 검색용 단어를 함께 비교
    texts = [
        " ".join([
            doc["title"],
            doc["section"],
            doc["excerpt"],
            " ".join(doc.get("keywords", [])),
        ])
        for doc in documents
    ]

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        sublinear_tf=True,
    )

    matrix = vectorizer.fit_transform(texts)
    question_vector = vectorizer.transform([question])

    scores = cosine_similarity(
        question_vector, matrix
    )[0]

    results = []

    for doc, score in zip(documents, scores):
        score = float(score)

        # 관련성이 지나치게 낮은 결과 제외
        # 임시 기준이며 실제 질문으로 조정할 예정
        if score < 0.10:
            continue

        results.append({
            **doc,
            "score": round(score, 4),
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:limit]


class RagAnswer(BaseModel):
    answer: str = Field(description="검색 근거로 확인되는 답변")
    evidence_ids: list[str] = Field(
        description="답변에 실제 사용한 근거 ID"
    )


RAG_INSTRUCTIONS = """
너는 서울 교통안전 뉴스룸의 근거 검색 조수다.

규칙:
1. 제공된 공식 문서 발췌문만 사실 근거로 사용한다.
2. 일반 지식이나 학습한 법령 내용을 보충하지 않는다.
3. 검색된 문단이 질문의 답을 직접 뒷받침하지 못하면
   '제공된 근거만으로는 확인할 수 없습니다.'라고 답하고
   evidence_ids는 빈 목록 []으로 반환한다.
   검색 유사도가 높다는 이유만으로 답하지 않는다.
   문단이 질문의 일부만 뒷받침하면 확인된 범위만 답하고
   빠진 내용은 확인할 수 없다고 명시한다.
4. 일부만 확인되는 경우 확인된 내용과
   확인할 수 없는 내용을 명확히 구분한다.
5. 법령에 없는 지정 기준, 정책 효과, 사고 원인을 만들지 않는다.
6. 정책 발표·계획·검토를 실제 시행으로 표현하지 않는다.
7. evidence_ids에는 실제 답변을 뒷받침하는
   근거 ID만 포함한다.
8. 답변은 간결한 한국어로 작성한다.
9. 질문에 직접 필요한 내용만 답한다.
10. 같은 조항에 원칙과 예외가 함께 제공되면 둘을 구분한다.
11. 지정 전 조사와 지정 이후의 정기 실태조사를 혼동하지 않는다.
"""



def search_statistics(question: str) -> dict | None:
    """기존 CSV와 Fact Sheet에서 질문에 필요한 통계를 조회한다."""

    # 법령·정책의 설명을 묻는 질문은 문서 RAG로 보낸다.

    policy_words = (
        "지정 기준", "지정기준", "지정 대상",
        "지정대상", "지정 전", "지정 범위",
        "법령", "법적 근거", "절차",
        "조사하", "실태조사", "정책", "시행",
        "경찰", "몇 미터", "예산",
    )

    if any(word in question for word in policy_words):
        return None

    # 숫자 조회 질문만 통계 검색으로 처리한다.
    metric_words = (
        "사고", "사망", "고령인구",
        "보호구역", "다발지역", "부상",
    )
    number_words = (
        "몇", "건수", "수는", "얼마",
        "비율", "차이", "비교", "중첩",
        "겹치", "많", "적", "1만 명당",
        "1만명당",
    )

    if not (
        any(w in question for w in metric_words)
        and any(w in question for w in number_words)
    ):
        return None

    def unavailable(message):
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer": message,
            "evidence": [],
        }

    state = dataset_state()
    if state["missing"]:
        return unavailable("사고 통계 파일이 누락됐습니다.")

    data = load_data(state["directory"], state["versions"])
    panel = data["panel"]

    years = list(dict.fromkeys(
        int(y) for y in re.findall(r"20\d{2}", question)
    ))

    districts = [
        d for d in panel["자치구명"].dropna().unique()
        if isinstance(d, str) and d in question
    ]

    if "서울 전체" in question:
        districts.append("서울 전체")

    if len(years) != 1 or len(districts) not in (1, 2):
        return {
            "status": "NEEDS_CLARIFICATION",
            "answer": "조회할 연도와 자치구를 명시해 주세요.",
            "evidence": [],
        }

    year = years[0]

    # 질문이 요구하는 수치를 구분한다.
    if "겹치" in question or "중첩" in question:
        metric = "overlap"
    elif "다발지역" in question:
        metric = "hotspots"
    elif "보호구역" in question:
        metric = "zones"
    elif "1만 명당" in question or "1만명당" in question:
        metric = "rate"
    elif "사망" in question:
        metric = "deaths"
    elif "고령인구" in question and "사고" not in question:
        metric = "population"
    else:
        metric = "accidents"

    metric_info = {
        "accidents": ("고령 보행자 사고 건수", "건"),
        "deaths": ("고령 보행자 사망자", "명"),
        "population": ("65세 이상 고령인구", "명"),
        "rate": ("고령인구 1만 명당 고령 보행자 사고", "건"),
        "zones": ("노인보호구역 명단 시설", "곳"),
        "hotspots": ("선정된 사고다발지역", "곳"),
        "overlap": ("보호구역과 중첩된 사고다발지역", "곳"),
    }

    label, unit = metric_info[metric]

    # 각 지역의 기존 Fact Sheet와 패널 값을 조회한다.
    values = {}
    evidence = []

    for district in districts:
        facts = fact_sheet(
            panel, data["links"], year, district
        )

        if facts["calculation_status"] != "CHECKED":
            return unavailable(
                f"{year}년 {district}의 확인 가능한 통계가 없습니다."
            )

        if metric == "accidents":
            value = facts["accidents"]
        elif metric == "deaths":
            value = facts["elderly_pedestrian_deaths"]
        elif metric == "population":
            value = facts["elderly_residents"]
        elif metric == "rate":
            value = facts["accidents_per_10000_residents"]
        else:
            rows = panel[
                (panel["사고연도"] == year)
                & (panel["자치구명"] == district)
            ]

            if len(rows) != 1:
                return unavailable(
                    "해당 지역의 상세 집계를 확인할 수 없습니다."
                )

            column = {
                "zones": "보호구역_명단시설수",
                "hotspots": "다발지역_수",
                "overlap": "다발지역_보호구역중첩수",
            }[metric]

            value = rows.iloc[0][column]

        if value is None or not pd.notna(value):
            return unavailable(
                f"{year}년 {district}의 해당 수치가 없습니다."
            )

        values[district] = float(value)

        evidence.append({
            "id": f"DATA-PANEL-{year}-{district}",
            "title": "자치구·연도별 보행자 안전 통계",
            "source_type": "STATISTIC",
            "source_file": "data/01_자치구연도_패널.csv",
            "related_file": "data/06_다발지역_보호구역_연결.csv",
            "year": year,
            "district": district,
            "metric": metric,
            "column": (
                {
                    "accidents": "고령보행자_사고건수",
                    "deaths": "고령보행자_사망자수",
                    "population": "고령인구",
                    "rate": "고령인구1만명당_고령보행자사고",
                    "zones": "보호구역_명단시설수",
                    "hotspots": "다발지역_수",
                    "overlap": "다발지역_보호구역중첩수",
                }[metric]
            ),
            "calculation_status": facts["calculation_status"],
            "limitations": facts["limitations"],
        })

    def display(n):
        if metric == "rate":
            return f"{n:,.2f}"
        return f"{n:,.0f}"

    if len(districts) == 1:
        district = districts[0]
        answer = (
            f"{year}년 {district}의 {label}은 "
            f"{display(values[district])}{unit}입니다."
        )
    else:
        first, second = districts
        difference = abs(values[first] - values[second])

        answer = (
            f"{year}년 {label}은 "
            f"{first} {display(values[first])}{unit}, "
            f"{second} {display(values[second])}{unit}입니다. "
            f"차이는 {display(difference)}{unit}입니다."
        )

    if metric == "zones":
        answer += " 보호구역 명단 기준이며 경계 확보 건수와 다를 수 있습니다."

    if metric == "overlap":
        answer += (
            " 사고다발지역과 확보된 보호구역 경계의 "
            "공간적 중첩 수치로, 전체 사고의 중첩 비율은 아닙니다."
        )

    return {
        "status": "ANSWERED",
        "answer": answer,
        "evidence": evidence,
    }

def answer_question(question: str) -> dict:
    """통계 또는 공식 문서 근거로 질문에 답한다."""

    # 1. 기존 검증된 CSV 통계를 우선 조회
    statistics = search_statistics(question)

    if statistics is not None:
        return statistics

    # 2. 통계 질문이 아니면 기존 법령 RAG 실행
    sources = search_documents(question)

    if not sources:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer": "검색된 공식 문서에서 관련 근거를 찾지 못했습니다.",
            "evidence": [],
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    evidence_text = json.dumps(
        [
            {
                "id": source["id"],
                "title": source["title"],
                "section": source["section"],
                "excerpt": source["excerpt"],
            }
            for source in sources
        ],
        ensure_ascii=False,
    )

    client = OpenAI(
        api_key=api_key,
        timeout=40,
        max_retries=0,
    )

    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=RAG_INSTRUCTIONS,
        input=(
            f"기자 질문:\n{question}\n\n"
            f"검색된 공식 문서 발췌:\n{evidence_text}"
        ),
        text_format=RagAnswer,
    )

    result = response.output_parsed
    if result is None:
        raise ValueError("AI 답변 형식을 확인할 수 없습니다.")

    # AI가 제시한 ID가 실제 검색 결과에 있는지 확인
    source_by_id = {source["id"]: source for source in sources}

    if any(
        evidence_id not in source_by_id
        for evidence_id in result.evidence_ids
    ):
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer": "AI가 반환한 근거 ID를 확인할 수 없습니다.",
            "evidence": [],
        }

    selected_ids = list(dict.fromkeys(result.evidence_ids))

    if not selected_ids:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer": (
                "제공된 근거만으로는 질문에 답할 수 없습니다."
            ),
            "evidence": [],
        }

    return {
        "status": "ANSWERED",
        "answer": result.answer,
        "evidence": [
            source_by_id[evidence_id]
            for evidence_id in selected_ids
        ],
    }




if __name__ == "__main__":



    questions = [
        "2025년 동대문구 고령 보행자 사고는 몇 건?",
        "2025년 동대문구 사고다발지역 중 보호구역과 겹치는 곳은?",
        "2030년 동대문구 고령 보행자 사고 건수는?",
    ]



    for question in questions:
        print(f"\n질문: {question}")

        try:
            result = answer_question(question)

            print("상태:", result["status"])
            print("답변:", result["answer"])

            evidence = result.get("evidence", [])

            if not evidence:
                print("연결된 근거 없음")

            for item in evidence:
                print(f"근거 ID: {item['id']}")

                if item.get("source_type") == "STATISTIC":
                    print(f"원본 파일: {item['source_file']}")
                    print(f"관련 파일: {item['related_file']}")
                    print(f"집계 기준: {item['year']}년 {item['district']}")
                    print(f"계산 상태: {item['calculation_status']}")
                    print("해석상 한계:", " / ".join(item["limitations"]))
                else:
                    print(f"원문: {item['excerpt']}")
                    print(f"출처: {item['url']}")

        except Exception as error:
            print("오류:", error)

        print("-" * 50)

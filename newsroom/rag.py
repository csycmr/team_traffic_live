
"""공식 문서의 확인된 발췌문을 검색하는 최소 RAG 검색기."""


"""공식 문서 검색 및 근거 기반 AI 답변."""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

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
    """질문과 관련된 공식 문서 발췌문을 검색한다."""

    if not question.strip():
        return []

    documents = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    results = []

    # 여러 문서에서 공통으로 등장하는 일반적인 단어
    common_keywords = {"노인보호구역", "보호구역", "지정"}

    normalized_question = re.sub(r"\s+", "", question)

    for doc in documents:
        matches = [
            keyword
            for keyword in doc["keywords"]
            if re.sub(r"\s+", "", keyword) in normalized_question
        ]

        specific_matches = [
            keyword
            for keyword in matches
            if keyword not in common_keywords
        ]

        # 일반적인 단어만 일치한 경우 제외
        if not specific_matches:
            continue

        # 핵심 키워드 3점, 일반 키워드 1점
        score = sum(
            1 if keyword in common_keywords else 3
            for keyword in matches
        )

        results.append({
            **doc,
            "score": score,
            "matched_keywords": matches,
        })

    results.sort(key=lambda item: item["score"], reverse=True)

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
3. 질문에 필요한 사실이 발췌문에 없으면
   '제공된 근거만으로는 확인할 수 없습니다.'라고 답한다.
4. 일부만 확인되는 경우 확인된 내용과
   확인할 수 없는 내용을 명확히 구분한다.
5. 법령에 없는 지정 기준, 정책 효과, 사고 원인을 만들지 않는다.
6. 정책 발표·계획·검토를 실제 시행으로 표현하지 않는다.
7. evidence_ids에는 실제 답변을 뒷받침하는
   근거 ID만 포함한다.
8. 답변은 간결한 한국어로 작성한다.
"""


def answer_question(question: str) -> dict:
    """문서 검색 후 해당 근거만으로 AI 답변을 생성한다."""

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
        "노인보호구역 지정 대상은 어디인가?",
        "보호구역 지정 시 교통사고 현황을 조사하나?",
        "서울시의 2030년 보호구역 예산은 얼마인가?",
    ]

    for question in questions:
        print(f"\n질문: {question}")

        try:
            result = answer_question(question)

            print("상태:", result["status"])
            print("AI 답변:", result["answer"])

            for item in result["evidence"]:
                print(f"근거 ID: {item['id']}")
                print(f"원문: {item['excerpt']}")
                print(f"출처: {item['url']}")

        except Exception as error:
            print("오류:", error)

        print("-" * 50)

"""S03 draft authoring: verified statistics and directly checked excerpts only."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

from newsroom.persistence import checked_facts


class ArticleDraft(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def load_idea_context(engine: Engine, idea_id: int) -> dict:
    """Only DB-persisted evidence and fact-sheet may be used for article drafting."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT i.id, i.title, i.angle, i.readiness, i.news_value,
                   i.analysis_id, i.source_ids_json, i.reporting_gaps_json,
                   a.facts_json, a.source_info_json, a.verification_status,
                   a.data_as_of
            FROM story_ideas i
            JOIN analysis_snapshots a ON a.id = i.analysis_id
            WHERE i.id = :idea_id
        """), {"idea_id": idea_id}).mappings().first()
        if row is None:
            raise ValueError("저장된 기사거리를 찾을 수 없습니다.")
        idea = dict(row)
        idea["facts_json"] = _json(idea["facts_json"])
        idea["source_info_json"] = _json(idea["source_info_json"])
        idea["source_ids_json"] = _json(idea["source_ids_json"])
        idea["reporting_gaps_json"] = _json(idea["reporting_gaps_json"])
        if idea["verification_status"] != "PASSED" or not checked_facts(idea["facts_json"]):
            raise ValueError("검증된 분석 스냅샷만 기사 작성에 사용할 수 있습니다.")
        refs = []
        # JSON source IDs are not FKs: resolve and verify each before use.
        for doc_id in idea["source_ids_json"]:
            if not isinstance(doc_id, int):
                continue
            ref = conn.execute(text("""
                SELECT id, title, source_org, source_type, source_url,
                       published_at, content_excerpt, verification_status
                FROM source_documents WHERE id = :id
            """), {"id": doc_id}).mappings().first()
            if ref:
                refs.append(dict(ref))
        idea["sources"] = refs
        idea["verified_sources"] = [
            ref for ref in refs if ref["verification_status"] == "VERIFIED"
            and ref["content_excerpt"] and ref["content_excerpt"].strip()
        ]
        return idea


DRAFTING_RULES = """당신은 한국 데이터 저널리즘 뉴스룸의 기사 초안 작성 보조자다.
검증된 Fact Sheet의 통계 수치와 직접 대조한 외부 발췌문만 사실 근거로 사용한다.
RSS 제목·링크·발행처만 있는 METADATA_ONLY 자료는 본문 속 사실 근거로 사용할 수 없다.
취재 메모, AI가 제안한 가제·취재 방향·정보 공백은 검증된 사실이 아니다.
기자 작성 지침은 기사 구성과 강조점에 관한 요청이다. 지침에 포함된 사실 주장은 별도로 검증된 근거가 없다면 본문에 사실로 단정하지 마라.
기자 지침과 검증된 Fact Sheet가 충돌하면 검증된 Fact Sheet를 우선하고, 확인되지 않은 인용·통계·원인을 창작하지 마라.
미확인 행정 결정, 사고 원인, 보호구역 정책의 실패·예방 효과를 단정하지 마라.
고령 보행자 사고는 발생지 기준, 고령인구는 거주지 기준이다.
사고다발지역의 중첩/비중첩은 선정된 폴리곤 수이지 개별 사고 발생 비율이 아니다.
현재 확보한 API 보호구역 경계에는 누락이 있을 수 있다.
정책 발표·계획과 실제 시행은 구분한다. 원문에 없는 인용·전문가 발언·현장 취재를 창작하지 마라.
기사 가치가 미확인 사실에 의존하면 그 주장을 제외하고 확인된 통계 중심으로 축소 작성한다.
관련성이 부족하면 통계의 의미와 한계에 충실한 짧은 기초 기사로 작성한다.
한국어 스트레이트 기사 형식: 제목, 리드, 본문 2~5문단. 과장 없는 간결한 문체.
결과는 ArticleDraft(title, content)의 구조화된 출력으로 반환한다.
초안은 검수·승인되지 않았으며 사실 검증 완료라고 쓰지 않는다.
"""


def generate_draft(context: dict, reporter_guidance: str = "") -> ArticleDraft:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    verified = [
        {"id": ref["id"], "org": ref["source_org"], "title": ref["title"],
         "published_at": ref["published_at"].isoformat() if ref["published_at"] else None,
         "url": ref["source_url"], "excerpt": ref["content_excerpt"]}
        for ref in context["verified_sources"]
    ]
    payload = {
        "analysis_id": context["analysis_id"],
        "facts": context["facts_json"],
        "source_information": context["source_info_json"],
        "data_as_of": context["data_as_of"].isoformat() if context["data_as_of"] else None,
        "reporting_angle_unverified": context["angle"],
        "suggested_title_unverified": context["title"],
        "reporting_gaps_not_facts": context["reporting_gaps_json"],
        "reporter_requested_emphasis_unverified": reporter_guidance,
        "verified_reference_excerpts": verified,
    }
    client = OpenAI(api_key=api_key, timeout=40, max_retries=0)
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=DRAFTING_RULES,
        input=json.dumps(payload, ensure_ascii=False, default=str),
        text_format=ArticleDraft,
    )
    result = response.output_parsed
    if not result or not result.title.strip() or not result.content.strip():
        raise RuntimeError("AI가 제목과 본문을 생성하지 못했습니다.")
    return result


def _validated_text(title: str, content: str):
    title, content = title.strip(), content.strip()
    if not title or not content:
        raise ValueError("기사 제목과 본문을 모두 입력하세요.")
    if "\n" in title or len(title) > 500:
        raise ValueError("제목은 한 줄, 500자 이내로 작성하세요.")
    return title, content


def draft_for_idea(engine: Engine, idea_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, story_idea_id, title, content, status, updated_at, reporter_guidance, validation_result
            FROM articles WHERE story_idea_id=:id ORDER BY id DESC LIMIT 1
        """), {"id": idea_id}).mappings().first()
    result = dict(row) if row else None
    if result: result['validation_result'] = _json(result['validation_result']) if result['validation_result'] else None
    return result


def save_draft(engine: Engine, context: dict, title: str, content: str,
               existing: dict | None = None, reporter_guidance: str = "") -> int:
    title, content = _validated_text(title, content)
    if context["verification_status"] != "PASSED" or not checked_facts(context["facts_json"]):
        raise ValueError("검증된 분석 스냅샷이 필요합니다.")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        if existing:
            result = conn.execute(text("""
                UPDATE articles SET title=:title, content=:content,
                    validation_passed=FALSE, validation_result=NULL, validated_hash=NULL,
                    status='검토대기', reviewed_by=NULL, reviewed_at=NULL,
                    review_note=NULL, published_at=NULL, updated_at=:now
                WHERE id=:id AND story_idea_id=:idea_id AND status='검토대기'
                  AND title=:old_title AND content=:old_content
            """), {"id": existing["id"], "idea_id": context["id"],
                    "title": title, "content": content, "now": now,
                    "old_title": existing["title"], "old_content": existing["content"]})
            if result.rowcount != 1:
                raise RuntimeError("기사가 다른 화면에서 수정되었거나 검토대기 상태가 아닙니다. 다시 불러오세요.")
            return int(existing["id"])
        result = conn.execute(text("""
            INSERT INTO articles
              (story_idea_id, title, content, status, validation_passed,
               validation_result, validated_hash, created_at, updated_at, reporter_guidance)
            VALUES (:idea_id, :title, :content, '검토대기', FALSE,
                    NULL, NULL, :now, :now, :guidance)
        """), {"idea_id": context["id"], "title": title, "content": content, "now": now,
             "guidance": reporter_guidance})
        article_id = int(result.lastrowid)
        conn.execute(text("""
            INSERT INTO article_evidence (article_id, analysis_id, source_document_id,
                evidence_role, location_label, explanation)
            VALUES (:article_id, :analysis_id, NULL, 'STATISTIC', :location,
                :explanation)
        """), {"article_id": article_id, "analysis_id": context["analysis_id"],
                "location": f'{context["facts_json"]["accident_year"]}년 · {context["facts_json"]["region"]}',
                "explanation": "고령 보행자 사고·인구·선정 사고다발지역 관련 통계 근거"})
        for ref in context["verified_sources"]:
            conn.execute(text("""
                INSERT INTO article_evidence (article_id, analysis_id,
                    source_document_id, evidence_role, location_label, explanation)
                VALUES (:article_id, NULL, :source_id, 'CONTEXT', :location, :explanation)
            """), {"article_id": article_id, "source_id": ref["id"],
                    "location": "기자 원문 대조 발췌",
                    "explanation": "직접 대조한 발췌에 한정된 맥락 근거"})
    return article_id


def load_draft(engine: Engine, article_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT id, story_idea_id, title, content, status, validation_passed,
                   updated_at, reporter_guidance, validation_result FROM articles WHERE id=:id
        """), {"id": article_id}).mappings().first()
    if not row:
        raise ValueError("저장된 기사 초안을 찾지 못했습니다.")
    result = dict(row)
    result['validation_result'] = _json(result['validation_result']) if result['validation_result'] else None
    return result

def attach_rag_law_evidence(
    engine: Engine,
    article_id: int,
    evidence_id: str,
    original_checked: bool = False,
) -> dict:
    """RAG 법령 근거를 기존 기사 근거 테이블에 연결한다."""
    import hashlib
    from pathlib import Path

    source_path = Path(__file__).resolve().parents[1] / "data" / "rag_sources.json"
    sources = json.loads(source_path.read_text(encoding="utf-8"))
    source = next((s for s in sources if s["id"] == evidence_id), None)

    if not source or not evidence_id.startswith(("LAW-", "RULE-")):
        raise ValueError("연결할 수 있는 법령 근거 ID가 아닙니다.")

    url = source.get("url", "")
    excerpt = source.get("excerpt", "").strip()
    
    from urllib.parse import urlparse

    parsed = urlparse(url)

    if parsed.scheme != "https" or parsed.hostname not in {
        "law.go.kr",
        "www.law.go.kr",
    }:
        raise ValueError("공식 법령 원문 주소가 아닙니다.")

    if not excerpt:
        raise ValueError("법령 발췌문이 없습니다.")

    verification = "VERIFIED" if original_checked else "METADATA_ONLY"
    
    source_hash = hashlib.sha256(
        f"RAG:{evidence_id}:{url}".encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with engine.begin() as conn:
        article = conn.execute(text("""
            SELECT id, status FROM articles
            WHERE id = :id FOR UPDATE
        """), {"id": article_id}).mappings().first()

        if not article:
            raise ValueError("기사를 찾을 수 없습니다.")
        if article["status"] != "검토대기":
            raise ValueError("검토대기 기사에만 근거를 연결할 수 있습니다.")

        conn.execute(text("""
            INSERT INTO source_documents (
                title, source_org, source_type, source_url,
                published_at, retrieved_at, content_excerpt,
                content_hash, verification_status
            )
            VALUES (
                :title, :org, 'POLICY', :url,
                NULL, :retrieved, :excerpt, :hash, :verification
            )
            ON DUPLICATE KEY UPDATE
                retrieved_at = VALUES(retrieved_at),
                content_excerpt = CASE
                    WHEN VALUES(verification_status) = 'VERIFIED'
                    THEN VALUES(content_excerpt)
                    ELSE content_excerpt
                END,
                verification_status = CASE
                    WHEN VALUES(verification_status) = 'VERIFIED'
                    THEN 'VERIFIED'
                    ELSE verification_status
                END
        """), {
            "title": source["title"][:500],
            "org": source.get("organization", "법제처")[:200],
            "url": url,
            "retrieved": now,
            "excerpt": excerpt if original_checked else None,
            "hash": source_hash,
            "verification": verification,
        })

        document = conn.execute(text("""
            SELECT id, verification_status
            FROM source_documents
            WHERE content_hash = :hash
        """), {"hash": source_hash}).mappings().one()

        existing = conn.execute(text("""
            SELECT id FROM article_evidence
            WHERE article_id = :article_id
              AND source_document_id = :document_id
        """), {
            "article_id": article_id,
            "document_id": document["id"],
        }).scalar_one_or_none()

        if existing is None:
            conn.execute(text("""
                INSERT INTO article_evidence (
                    article_id, analysis_id, source_document_id,
                    evidence_role, location_label, explanation
                )
                VALUES (
                    :article_id, NULL, :document_id,
                    'CONTEXT', :location, :explanation
                )
            """), {
                "article_id": article_id,
                "document_id": document["id"],
                "location": source.get("section", "법령"),
                "explanation": f"RAG 근거 {evidence_id} · 기자 선택",
            })


        # 근거가 바뀌면 기존 검수 결과는 다시 확인해야 한다.
        conn.execute(text("""
            UPDATE articles SET
                validation_passed = FALSE,
                validation_result = NULL,
                validated_hash = NULL,
                reviewed_by = NULL,
                reviewed_at = NULL,
                review_note = NULL,
                updated_at = :now
            WHERE id = :article_id
        """), {"article_id": article_id, "now": now})

    return {
        "article_id": article_id,
        "evidence_id": evidence_id,
        "source_document_id": int(document["id"]),
        "verification_status": document["verification_status"],
        "linked": True,
    }


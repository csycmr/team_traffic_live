"""Flask 대시보드와 기존 API. 통계·CCTV·도시데이터 계산은 app.services를 함께 쓴다."""

import os
import re
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, jsonify, request, send_from_directory

from app.config import load_settings
from app.errors import ServiceError
from app.services import accident_service, cctv_service, citydata_service

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
app = Flask(__name__, static_folder=None)


@app.errorhandler(ServiceError)
def handle_service_error(error):
    return jsonify(error.payload()), error.status_code


from newsroom.data import dataset_state, load_data
from newsroom.recommendation import fact_sheet


@app.get("/api/newsroom/facts")
def newsroom_facts():
    from flask import request

    year = request.args.get("year", default=2025, type=int)
    district = request.args.get("district", default="동대문구")

    try:
        state = dataset_state()

        if state["missing"]:
            return jsonify(error="분석 데이터가 누락됐습니다."), 503

        data = load_data(state["directory"], state["versions"])
        facts = fact_sheet(data["panel"], data["links"], year, district)

        if facts["calculation_status"] != "CHECKED":
            return jsonify(error="확인 가능한 Fact Sheet가 없습니다."), 422

        return jsonify(facts)

    except (OSError, ValueError, KeyError) as error:
        return jsonify(error=str(error)), 400

from newsroom.article_draft import (
    load_idea_context,
    generate_draft,
    save_draft,
    draft_for_idea,
)


@app.get("/api/newsroom/ideas")
def newsroom_saved_ideas():
    engine = None
    try:
        engine = engine_from_env()
        ideas = recent_saved_ideas(engine, limit=50)
        return jsonify(ideas=ideas, count=len(ideas))
    except Exception:
        app.logger.exception("저장된 기사거리 조회 실패")
        return jsonify(error="저장된 기사거리를 불러오지 못했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()


@app.get("/api/newsroom/ideas/<int:idea_id>/draft")
def newsroom_existing_idea_draft(idea_id):
    engine = None
    try:
        engine = engine_from_env()
        result = draft_for_idea(engine, idea_id)
        return jsonify(draft=result)
    except Exception:
        app.logger.exception("기사거리의 기존 초안 조회 실패")
        return jsonify(error="기존 초안을 불러오지 못했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()


@app.post("/api/newsroom/drafts")
def newsroom_create_draft():
    from flask import request

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON 입력이 필요합니다."), 400

    engine = None

    try:
        idea_id = int(payload["idea_id"])
        engine = engine_from_env()

        guidance = payload.get("reporter_guidance", "")
        if not isinstance(guidance, str) or len(guidance) > 3000:
            return jsonify(error="기자 작성 지침은 3000자 이내 텍스트로 입력하세요."), 400
        context = load_idea_context(engine, idea_id)
        if draft_for_idea(engine, idea_id) is not None:
            return jsonify(error="이미 초안이 있습니다. 기존 초안을 불러와 수정하세요."), 409
        draft = generate_draft(context, reporter_guidance=guidance.strip())

        result = save_draft(
            engine,
            context,
            draft.title,
            draft.content,
            reporter_guidance=guidance,
        )

        return jsonify(result), 201

    except (ValueError, KeyError, TypeError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        app.logger.exception("기사 초안 생성 실패")
        return jsonify(error="기사 초안 생성 중 오류가 발생했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()

from newsroom.recommendation import (
    search_sources,
    recommend,
    validate_hint_url,
)

from newsroom.persistence import engine_from_env, save_idea, recent_saved_ideas


@app.post("/api/newsroom/ideas")
def newsroom_save_idea():
    from flask import request

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON 입력이 필요합니다."), 400

    try:
        recommendation = payload["recommendation"]
        index = payload["selected_index"]

        if not isinstance(recommendation, dict):
            raise ValueError("추천 결과 형식이 잘못됐습니다.")
        if type(index) is not int:
            raise ValueError("선택 번호가 올바르지 않습니다.")

        ideas = recommendation["ideas"]
        sources = recommendation["search"]["sources"]
        submitted_facts = recommendation["facts"]

        if not isinstance(ideas, list) or not isinstance(sources, list):
            raise ValueError("추천 후보 또는 출처 형식이 잘못됐습니다.")
        if not isinstance(submitted_facts, dict):
            raise ValueError("Fact Sheet 형식이 잘못됐습니다.")
        if index < 0 or index >= len(ideas):
            raise ValueError("선택한 후보가 없습니다.")

        # 저장 전 서버에서 원본 CSV로 Fact Sheet를 다시 계산한다.
        state = dataset_state()
        if state["missing"]:
            return jsonify(error="분석 데이터가 누락됐습니다."), 503

        data = load_data(state["directory"], state["versions"])
        facts = fact_sheet(
            data["panel"],
            data["links"],
            int(submitted_facts["accident_year"]),
            str(submitted_facts["region"]),
        )

        if facts["calculation_status"] != "CHECKED":
            raise ValueError("Fact Sheet를 확인할 수 없습니다.")

        if facts != submitted_facts:
            raise ValueError("추천 당시 Fact Sheet와 현재 데이터가 다릅니다.")

        idea = ideas[index]
        if not isinstance(idea, dict):
            raise ValueError("기사거리 형식이 잘못됐습니다.")

        # 기자가 원문을 직접 대조하지 않았으므로 VERIFIED로 저장하지 않는다.
        engine = engine_from_env()
        try:
            idea_id = save_idea(
                engine,
                facts,
                idea,
                sources,
                verified_excerpts={},
            )
        finally:
            engine.dispose()

        return jsonify(
            id=idea_id,
            title=idea["title"],
            readiness="NEEDS_REPORTING",
            saved=True,
        ), 201

    except (KeyError, ValueError, TypeError, IndexError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        app.logger.exception("기사거리 저장 실패")
        return jsonify(error="기사거리 저장 중 오류가 발생했습니다."), 500

@app.post("/api/newsroom/recommend")
def newsroom_recommend():
    from flask import request

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON 입력이 필요합니다."), 400

    try:
        year = int(payload.get("year", 2025))
        district = str(payload.get("district", "동대문구"))
        days = int(payload.get("days", 30))
        categories = payload.get(
            "categories", ["정책", "보도자료", "언론"]
        )
        keyword = str(payload.get("keyword", "")).strip()
        url = validate_hint_url(str(payload.get("url", "")))
        memo = str(payload.get("memo", "")).strip()

        if not isinstance(categories, list) or not all(
            isinstance(c, str) for c in categories
        ):
            return jsonify(error="검색 유형 형식이 잘못됐습니다."), 400

        state = dataset_state()
        if state["missing"]:
            return jsonify(error="분석 CSV가 누락됐습니다."), 503

        data = load_data(state["directory"], state["versions"])
        panel = data["panel"]

        valid_districts = set(panel["자치구명"].dropna())
        if district != "서울 전체" and district not in valid_districts:
            return jsonify(error="지원하지 않는 자치구입니다."), 400

        facts = fact_sheet(data["panel"], data["links"], year, district)
        if facts["calculation_status"] != "CHECKED":
            return jsonify(error="Fact Sheet를 확인할 수 없습니다."), 422

        search = search_sources(days, categories, keyword)
        ideas = recommend(facts, search, keyword, url, memo)

        return jsonify(
            facts=facts,
            search=search,
            ideas=ideas,
            count=len(ideas),
        )

    except (ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        app.logger.exception("기사거리 추천 실패")
        return jsonify(error="기사거리 추천 중 오류가 발생했습니다."), 502

@app.get("/")
def dashboard():
    kakao_key = os.getenv("KAKAO_MAP_JS_KEY", "").strip()
    if not kakao_key:
        return send_from_directory(ROOT, "seoul-traffic-demo.html")

    html = (ROOT / "seoul-traffic-demo.html").read_text(encoding="utf-8")
    html = re.sub(
        r"(https://dapi\.kakao\.com/v2/maps/sdk\.js\?appkey=)[^&\"]+",
        lambda match: match[1] + quote(kakao_key, safe=""),
        html,
        count=1,
    )
    return Response(html, mimetype="text/html")


@app.get("/data/<path:filename>")
def dashboard_data(filename):
    return send_from_directory(DATA, filename)


@app.get("/assets/<path:filename>")
def dashboard_asset(filename):
    return send_from_directory(ROOT / "assets", filename)

@app.get("/newsroom")
def newsroom_page():
    return send_from_directory(ROOT, "newsroom.html")

@app.get("/api/cctv")
def cctv():
    return jsonify(cctv_service.seoul_cctv(load_settings().its_cctv_api_key))


@app.get("/api/statistics/elderly")
def elderly_statistics():
    """2025년 서울 고령 보행자 교통사고 통계 제공."""
    return jsonify(accident_service.elderly_pedestrian().model_dump())


@app.get("/api/statistics/elderly/districts")
def elderly_district_rates():
    """자치구별 고령 보행자 사고율과 전년 대비 변화."""
    return jsonify(accident_service.elderly_district_rates().model_dump())


@app.get("/api/citydata")
def citydata():
    """서울시 실시간 도시데이터를 기존 뉴스룸 JSON 형식으로 제공."""
    current = load_settings()
    place = request.args.get("place", "gwanghwamun")
    return jsonify(
        citydata_service.citydata(
            place, current.seoul_citydata_api_key, current.citydata_cache_seconds
        )
    )


from newsroom.article_draft import load_draft


@app.get("/api/newsroom/drafts/<int:article_id>")
def newsroom_get_draft(article_id):
    engine = engine_from_env()
    try:
        draft = load_draft(engine, article_id)
        return jsonify(draft)
    except ValueError as error:
        return jsonify(error=str(error)), 404
    finally:
        engine.dispose()


@app.put("/api/newsroom/drafts/<int:article_id>")
def newsroom_update_draft(article_id):
    from flask import request

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON 입력이 필요합니다."), 400

    engine = None
    try:
        engine = engine_from_env()
        existing = load_draft(engine, article_id)

        if existing["status"] != "검토대기":
            return jsonify(error="검토대기 기사만 수정할 수 있습니다."), 409

        context = load_idea_context(engine, existing["story_idea_id"])

        # 기존 원고와 비교해 다른 화면의 수정 내용을 보호한다.
        old_title = payload["old_title"]
        old_content = payload["old_content"]

        if (existing["title"] != old_title or
                existing["content"] != old_content):
            return jsonify(error="기사 내용이 변경됐습니다. 다시 불러오세요."), 409

        saved_id = save_draft(
            engine,
            context,
            payload["title"],
            payload["content"],
            existing=existing,
        )

        return jsonify(
            id=saved_id,
            saved=True,
            draft=load_draft(engine, saved_id),
        )

    except (KeyError, ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400
    except RuntimeError as error:
        return jsonify(error=str(error)), 409
    finally:
        if engine is not None:
            engine.dispose()

from newsroom.review import validate


@app.post("/api/newsroom/drafts/<int:article_id>/validate")
def newsroom_validate_draft(article_id):
    engine = None

    try:
        engine = engine_from_env()
        result = validate(engine, article_id)

        return jsonify(
            article_id=article_id,
            **result,
        )

    except ValueError as error:
        return jsonify(error=str(error)), 409

    except Exception:
        app.logger.exception("기사 자동 검수 실패")
        return jsonify(
            error="자동 검수 중 오류가 발생했습니다."
        ), 500

    finally:
        if engine is not None:
            engine.dispose()

from newsroom.review import decide, CHECKS


@app.get("/api/newsroom/editor/checklist")
def newsroom_editor_checklist():
    return jsonify(checks=CHECKS)


@app.post("/api/newsroom/drafts/<int:article_id>/decision")
def newsroom_editor_decision(article_id):
    from flask import request

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON 입력이 필요합니다."), 400

    engine = None
    try:
        action = payload["action"]
        if action not in ("approve", "hold"):
            return jsonify(error="approve 또는 hold를 선택하세요."), 400

        checks = payload["checks"]
        if not isinstance(checks, list) or len(checks) != 4 or not all(
            type(value) is bool for value in checks
        ):
            return jsonify(error="체크리스트 4개를 확인하세요."), 400

        engine = engine_from_env()
        status = decide(
            engine=engine,
            id=article_id,
            reviewer=payload["reviewer"],
            password=payload["password"],
            checks=checks,
            approve=(action == "approve"),
            note=payload.get("note", ""),
        )

        return jsonify(
            article_id=article_id,
            status=status,
            saved=True,
        )

    except (KeyError, ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        app.logger.exception("편집장 승인·보류 실패")
        return jsonify(error="편집장 결정 처리 중 오류가 발생했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()

from newsroom.publication import approved_articles, approved_article


@app.get("/api/newsroom/articles")
def newsroom_public_articles():
    engine = None
    try:
        engine = engine_from_env()
        articles = approved_articles(engine)

        return jsonify(
            articles=articles,
            count=len(articles),
        )

    except Exception:
        app.logger.exception("승인 기사 목록 조회 실패")
        return jsonify(error="승인 기사 목록을 불러오지 못했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()


@app.get("/api/newsroom/articles/<int:article_id>")
def newsroom_public_article(article_id):
    engine = None
    try:
        engine = engine_from_env()
        article = approved_article(engine, article_id)

        if article is None:
            return jsonify(error="공개된 기사를 찾을 수 없습니다."), 404

        return jsonify(article)

    except Exception:
        app.logger.exception("승인 기사 상세 조회 실패")
        return jsonify(error="기사를 불러오지 못했습니다."), 500
    finally:
        if engine is not None:
            engine.dispose()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=load_settings().flask_port)
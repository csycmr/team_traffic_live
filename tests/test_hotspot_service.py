import json

import pytest

from app.errors import ServiceError
from app.services import hotspot_service
from app.services.data_files import HOTSPOT_FILE, HOTSPOT_LINK_FILE, PANEL_FILE

HOTSPOT_HEADER = "다발지역FID,사고연도,자치구코드,자치구명,법정동명,부근명,지점명,사고건수,사망자수,경도,위도\n"
LINK_HEADER = "다발지역FID,사고연도,최단거리_m,경계중첩\n"
PANEL_HEADER = "자치구명,사고연도,고령인구,고령보행자_사고건수\n"


def write_all(write_csv, spots, links, panel="가구,2025,1000,20\n나구,2025,2000,10"):
    data_dir = write_csv(HOTSPOT_FILE, HOTSPOT_HEADER + spots)
    (data_dir / HOTSPOT_LINK_FILE).write_text(LINK_HEADER + links + "\n", encoding="utf-8-sig")
    (data_dir / PANEL_FILE).write_text(PANEL_HEADER + panel + "\n", encoding="utf-8-sig")
    return data_dir


SPOTS = "\n".join(
    [
        "1,2025,11110,가구,갑동,갑교차로 부근,서울특별시 가구 갑동(갑교차로 부근),5,1,127.0,37.5",
        "2,2025,11110,가구,을동,을시장 부근,서울특별시 가구 을동(을시장 부근),5,0,127.1,37.6",
        "3,2025,11140,나구,병동,병역 4호선 부근,서울특별시 나구 병동(병역 4호선 부근),3,0,127.2,37.7",
        "4,2024,11140,나구,정동,정교차로 부근,서울특별시 나구 정동(정교차로 부근),9,0,127.3,37.8",
    ]
)


def test_hotspots_are_2025_only_and_sorted(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\n2,2025,200.5,0\n3,2025,50,0")
    result = hotspot_service.hotspots(data_dir)
    assert result.year == 2025
    assert [h.id for h in result.locations] == ["1", "2", "3"]
    first = result.locations[0]
    assert first.name == "서울 가구 갑동(갑교차로 부근)"  # 서울특별시 → 서울
    assert (first.crashes, first.deaths, first.lat, first.lng) == (5, 1, 37.5, 127.0)


def test_review_counts_order_and_distance(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\n2,2025,200.5,0\n3,2025,50,0")
    review = hotspot_service.hotspot_review(data_dir, candidates=("가구", "나구"))
    assert (review.total, review.overlapping, review.outside, review.undetermined) == (3, 1, 2, 0)
    assert review.outside_percent == 66.7
    # 사고 많은 순, 같으면 가까운 순(겹침은 0m)
    assert [(i.name, i.overlaps, i.distance_m) for i in review.items] == [
        ("가구 갑동 갑교차로", True, None),
        ("가구 을동 을시장", False, 200),  # 200.5는 내린다
        ("나구 병동 병역 4호선", False, 50),
    ]
    assert [(d.district, d.overlapping, d.outside) for d in review.districts] == [
        ("가구", 1, 1),
        ("나구", 0, 1),
    ]
    assert [(c.district, c.selected, c.outside, c.overlapping, c.undetermined, c.accidents_per_10k)
            for c in review.candidates] == [("가구", 2, 1, 1, 0, 200.0), ("나구", 1, 1, 0, 0, 50.0)]


def test_unjudged_hotspot_counts_as_undetermined(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\n2,2025,,\n3,2025,50,0")
    review = hotspot_service.hotspot_review(data_dir, candidates=("가구",))
    assert (review.total, review.undetermined) == (2, 1)
    assert review.candidates[0].selected == 2 and review.candidates[0].undetermined == 1


def test_missing_link_row_is_undetermined_not_error(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\n3,2025,50,0")
    review = hotspot_service.hotspot_review(data_dir, candidates=("가구",))
    assert review.undetermined == 1


def test_unknown_candidate_is_error(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1\n2,2025,200,0\n3,2025,50,0")
    with pytest.raises(ServiceError, match="없어"):
        hotspot_service.hotspot_review(data_dir, candidates=("없는구",))


def test_no_hotspots_for_year_is_error(write_csv):
    data_dir = write_all(write_csv, SPOTS, "1,2025,0,1")
    with pytest.raises(ServiceError, match="없어"):
        hotspot_service.hotspots(data_dir, year=2030)


def test_duplicate_fid_is_error(write_csv):
    spots = SPOTS + "\n1,2025,11110,가구,갑동,갑교차로 부근,서울특별시 가구 갑동(갑교차로 부근),5,1,127.0,37.5"
    data_dir = write_all(write_csv, spots, "1,2025,0,1")
    with pytest.raises(ServiceError, match="겹쳐"):
        hotspot_service.hotspots(data_dir)


def test_real_locations_equal_json_file(real_data_dir):
    expected = json.loads((real_data_dir / "accident-hotspots-2025.json").read_text(encoding="utf-8"))
    assert hotspot_service.hotspots(real_data_dir).model_dump() == expected


def test_real_review_matches_page(real_data_dir):
    review = hotspot_service.hotspot_review(real_data_dir)
    assert (review.total, review.overlapping, review.outside, review.undetermined) == (71, 12, 59, 0)
    assert review.outside_percent == 83.1
    assert len(review.items) == 71 and len(review.districts) == 21
    top = [(i.name, i.crashes, "겹침" if i.overlaps else f"{i.distance_m}m") for i in review.items[:12]]
    assert top == [
        ("동대문구 제기동 동서시장", 12, "겹침"),
        ("동대문구 제기동 청량리전통시장", 10, "겹침"),
        ("동작구 상도동 계령약국", 10, "111m"),
        ("강북구 번동 수유역교차로", 7, "408m"),
        ("동작구 사당동 남성사계시장", 7, "451m"),
        ("성북구 길음동 길음역교차로", 7, "468m"),
        ("성북구 종암동 종암동주민센터", 7, "856m"),
        ("강북구 미아동 미아사거리역 4호선", 7, "1372m"),
        ("성북구 상월곡동 장위2동주민센터", 6, "겹침"),
        ("관악구 봉천동 낙성대역 2호선", 6, "겹침"),
        ("강동구 명일동 굽은다리역교차로", 6, "겹침"),
        ("동대문구 제기동 경동시장교차로", 6, "74m"),
    ]
    assert [(d.district, d.overlapping, d.outside) for d in review.districts[:6]] == [
        ("동대문구", 3, 7), ("중랑구", 0, 7), ("성북구", 1, 4),
        ("동작구", 1, 4), ("강동구", 1, 4), ("은평구", 0, 5),
    ]
    assert [(c.district, c.selected, c.outside, c.overlapping, c.undetermined, c.accidents_per_10k)
            for c in review.candidates] == [
        ("동대문구", 10, 7, 3, 0, 18.14), ("중랑구", 7, 7, 0, 0, 11.91),
        ("은평구", 5, 5, 0, 0, 11.42), ("금천구", 4, 4, 0, 0, 16.38),
    ]
    assert any(i.distance_m == 335 for i in review.items)  # 335.5m는 내림

# 데이터 흐름과 폴더 구조

화면의 통계값은 `공식 원자료 → 정제 CSV → app/services → JSON API → HTML 차트·카드` 순서로 연결한다.
HTML에는 API로 채우는 값을 직접 쓰지 않는다. 값 칸은 `—`로 두고, 로딩 스크립트가 API 응답으로 채운다. API가 꺼져 있으면 `—`로 남는다.

## 폴더

| 위치 | 역할 |
| --- | --- |
| `data/raw/` | 내려받은 공식 원자료(TAAS xlsx, OECD 원본 CSV). 수정하지 않는다. |
| `data/*.csv`, `data/*.geojson`, `data/*.json` | 정제 결과. 번호(01~22)가 자료 종류다. |
| `scripts/clean_oecd_13.py`, `taas_accident_trend_2020_2025.ipynb`, `seoul_traffic_preprocessing.ipynb` | 원자료를 정제 CSV로 만드는 코드 |
| `make_child_zone_list.py` | 어린이보호구역 지정현황 엑셀을 `21_`·`22_` 목록용 CSV로 바꾸는 도구 |
| `app/services/` | 정제 CSV를 읽어 값을 계산 (API가 아니라 함수). 파일 이름은 `data_files.py`에 모아 둔다. |
| `app/models.py` | API 응답 필드와 값 범위 |
| `app/main.py`, `app/flask_app.py` | 서비스 함수를 JSON으로 내보내는 얇은 라우트 |
| `scripts/apply_html_wiring.py` | `seoul-traffic-demo.html`에 API 연결 코드를 적용한다. 여러 번 실행해도 안전하다. |
| `tests/` | 서비스 값과 라우트 응답 검증 (`data/`의 실제 파일로 확인) |

`data/` 안의 파일 위치는 README 링크, 화면 JavaScript, Flask의 `/data/<파일>` 경로가 직접 참조하므로 옮기지 않았다.

## API와 자료

FastAPI(`app.main`)가 제공한다. 전체 목록은 `http://127.0.0.1:8000/docs`에서도 볼 수 있다.

### 교통사고·OECD

| API | 서비스 | 자료 |
| --- | --- | --- |
| `GET /api/oecd/rankings` | `oecd_service.oecd_rankings` | `13_OECD_고령지표_wide.csv` |
| `GET /api/traffic/accident-trend` | `accident_service.accident_trend` | `15_TAAS_시도시군구_교통사고_2020-2025.csv` |
| `GET /api/traffic/national-deaths` | `accident_service.national_deaths` | `17_전국사망자_막대도넛.csv` (연도별 전체 사망자는 TAAS 합계와 대조) |
| `GET /api/traffic/child-pedestrian` | `accident_service.child_pedestrian` | `10_어린이보호구역_교통안전_요약.csv` (보행자 교통사고 · 서울 · 2025 · 12세 이하, 정확히 1행) |
| `GET /api/traffic/child-camera-effect` | `accident_service.child_camera_effect` | `20_서울_어린이보호구역_무인단속카메라_전후.csv` (설치 전 2018~2019 · 후 2021~2022, 2행) |
| `GET /api/statistics/elderly-population` | `population_service.elderly_population` | `18_전국_65세이상_주민등록인구.csv` |

### 고령 보행사고·노인보호구역

| API | 서비스 | 자료 |
| --- | --- | --- |
| `GET /api/statistics/elderly` | `accident_service.elderly_pedestrian` | `01_자치구연도_패널.csv` (2025, 25개 자치구 합계) |
| `GET /api/statistics/elderly/districts` | `accident_service.elderly_district_rates` | `01_자치구연도_패널.csv` (자치구별 사고율·순위 변화) |
| `GET /api/statistics/elderly/zone-before-after` | `protection_service.zone_before_after` | `04_보호구역_마스터.csv` + `01_자치구연도_패널.csv` |
| `GET /api/statistics/elderly/district-comparison` | `comparison_service.district_comparison` | `01_자치구연도_패널.csv` (서울·동대문구·도봉구 4년) |
| `GET /api/statistics/hotspots` | `hotspot_service.hotspots` | `03_다발지역_서울.csv` (2025) |
| `GET /api/statistics/hotspots/review` | `hotspot_service.hotspot_review` | `03_다발지역_서울.csv` + `06_다발지역_보호구역_연결.csv` + `01_자치구연도_패널.csv` |

### 보호구역·예산

| API | 서비스 | 자료 |
| --- | --- | --- |
| `GET /api/protection-zones` | `protection_map_service.protection_zones` | `04_보호구역_마스터.csv` + `05_보호구역_경계.csv` |
| `GET /api/protection-zones/boundaries` | `protection_map_service.protection_boundaries` | `05_보호구역_경계.csv` |
| `GET /api/school-zones` | `protection_map_service.school_zones` | `09_어린이보호구역_서울.csv` (지도에 찍는 좌표 목록) |
| `GET /api/statistics/zone-overview` | `protection_service.zone_overview` | `11_서울_연령별_주민등록인구_202609.csv` + `12_경찰청_어린이보호구역_지정현황_20260630.csv` + `04_보호구역_마스터.csv` |
| `GET /api/budget/zone-improvement` | `budget_service.zone_budget` | `14_서울시예산_2026.csv` + 어린이 구역 수 `21_…20251231_목록용.csv`(2025년 예산)·`22_…20260630_목록용.csv`(2026년 예산) + 노인 구역 수 `04_보호구역_마스터.csv` |

### 외부 API(Flask)

| API | 서비스 | 자료 |
| --- | --- | --- |
| `GET /api/cctv` | `cctv_service.seoul_cctv` | ITS API + `08_서울_자치구_경계.geojson` |
| `GET /api/citydata` | `citydata_service.citydata` | 서울시 도시데이터 API |

오류는 `ServiceError`로 올리고, 응답은 `{"error": 메시지}` 형태다.
읽는 열이 없거나, 같은 행이 겹치거나, 값이 비어 있으면 조용히 넘어가지 않고 오류로 끝낸다.

## 정제 CSV

| 번호 | 파일 | 내용 | 쓰는 곳 |
| --- | --- | --- | --- |
| 01 | `01_자치구연도_패널.csv` | 자치구·연도별 고령인구, 고령 보행자 사고 | 사고율, 지정 전후, 4년 비교, 검토 표 |
| 02 | `02_사고상세_동대문도봉.csv` | 동대문·도봉 사고 상세 | 분석 노트북 |
| 03 | `03_다발지역_서울.csv` | 사고다발지역 | 사고다발지역 API |
| 04 | `04_보호구역_마스터.csv` | 노인보호구역 명단(시설ID, 지정 연도, 연도별 명단) | 지도, 지정 전후, 현황, 예산 |
| 05 | `05_보호구역_경계.csv` | 노인보호구역 경계(WKT) | 지도, 중첩 판정 |
| 06 | `06_다발지역_보호구역_연결.csv` | 사고다발지역과 가장 가까운 보호구역·경계 중첩 | 검토 API |
| 07 | `07_다발지역_보호구역_500m쌍.csv` | 사고다발지역–보호구역 500m 쌍 | 분석 노트북 |
| 08 | `08_서울_자치구_경계.geojson` | 서울·자치구 경계 | 지도, CCTV 필터 |
| 09 | `09_어린이보호구역_서울.csv` | 전국어린이보호구역표준데이터의 서울 시설(좌표 포함) | 지도의 어린이보호구역 |
| 10 | `10_어린이보호구역_교통안전_요약.csv` | 어린이 보행사고 집계 | 어린이 보행사고 API |
| 11 | `11_서울_연령별_주민등록인구_202609.csv` | 서울 연령별 인구(2026년 9월 말) | 보호구역 현황 |
| 12 | `12_경찰청_어린이보호구역_지정현황_20260630.csv` | 경찰청 지정 현황 합계(시도별) | 보호구역 현황 |
| 13 | `13_OECD_고령지표_wide.csv`, `13_OECD_정제.csv` | OECD 65세 이상 사망률 | OECD 순위 API (`scripts/clean_oecd_13.py`로 정제) |
| 14 | `14_서울시예산_2026.csv` | 서울시 2026년 예산서 텍스트 행(PDF쪽 단위) | 보호구역 개선 예산 |
| 15 | `15_TAAS_시도시군구_교통사고_2020-2025.csv` | TAAS 시도·시군구 교통사고 | 사고 추이 |
| 16 | `16_경찰청_2024-2025_교통사고_요약.csv` | 경찰청 2024~2025 교통사고 요약 | 서비스에서 직접 읽지 않음(참고) |
| 17 | `17_전국사망자_막대도넛.csv` | 전국·65세 이상 사망자, 사고 당시 상태 | 전국 사망자 막대, 상태 도넛 |
| 18 | `18_전국_65세이상_주민등록인구.csv` | 전국 65세 이상 주민등록인구(월말) | 인구 추이 |
| 20 | `20_서울_어린이보호구역_무인단속카메라_전후.csv` | 서울시 카메라 107대 설치 전후 | 카메라 전후 |
| 21 | `21_서울_어린이보호구역_지정현황_20251231_목록용.csv` | 2025년 12월 31일 기준 지정 시설 목록 | 예산 표(2025년 구역 수) |
| 22 | `22_서울_어린이보호구역_지정현황_20260630_목록용.csv` | 2026년 6월 30일 기준 지정 시설 목록 | 예산 표(2026년 구역 수) |
| - | `accident-hotspots-2025.json` | 사고다발지역 원본 JSON | 테스트가 API 값과 같은지 대조 |
| - | `검수_명단_API_매칭.csv` | 보호구역 명단과 API 매칭 검수 | 분석 노트북 |

### 열 설명

- `15_TAAS_시도시군구_교통사고_2020-2025.csv`: `연도, 시도, 시군구, 사고건수, 사망자수, 부상자수` (세로형, 2020~2025). 시군구가 `합계`인 행이 시도 합계, 시도가 `합계`인 행이 전국 합계. 전국 합계 행은 17개 시도 합계의 합보다 해마다 조금 크다(원본 특성). 추이 API는 전국 합계·서울 합계 행을 쓴다(2025: 193,889건 / 서울 34,309건·45,446명·212명).
- `10_어린이보호구역_교통안전_요약.csv`: `자료구분, 지역, 사고연도, 연령범위, 사고건수, 사망자수, 부상자수, 보호구역기록수, 자료기준일, 출처`
- `20_…카메라_전후.csv`: `구분, 기간, 어린이_보행사고, 전체_보행사고, 어린이_보행부상자, 전체_보행부상자, 설치대수, 출처`. `설치 전`·`설치 후` 각 1행.
- `21_`·`22_…목록용.csv`: `기준일, 자치구, 행정동, 도로명주소, 시설명, 시설유형, 지정연도, 원본연번`. 시설 한 곳이 한 줄이고 행 수가 곧 지정 구역 수다. 한 파일 안의 `기준일`이 모두 파일명 날짜와 같아야 한다. 아니면 예산 API가 오류를 낸다.
- `14_서울시예산_2026.csv`: `PDF쪽, 인쇄쪽, PDF쪽_텍스트행, 구분, 행유형, 항목, 예산과목코드, 2025예산_천원, 2026예산_천원, 증감_천원, …`. 예산 API는 `세출예산`·`연도별 예산 비교` 행에서 `어린이보호구역개선(전환사업)`과 `노인·장애인보호구역개선(전환사업)`을 공백 없이 찾고, 각각 정확히 한 행이어야 한다. 단위는 천원이며 1곳당 환산액은 `예산 ÷ 구역 수`를 만 원 단위로 반올림한다.

## 자료를 새로 받았을 때

1. 공식 원본을 `data/raw/`에 두거나 정제한다. 엑셀 지정현황은 아래 도구로 CSV를 만든다.
   ```powershell
   .\.venv\Scripts\python.exe make_child_zone_list.py "엑셀파일.xlsx" 21
   ```
   파일 이름은 엑셀 머리글의 날짜에서 만든다. 엑셀 합계·자치구 소계와 행 수가 다르면 만들지 않는다. `openpyxl`이 필요하다.
2. 새 파일 이름을 `app/services/data_files.py`에 적는다. 예산 표의 어린이 구역 수는 `CHILD_LIST_FILES`의 날짜와 파일을 바꾼다.
3. `python -m pytest -q`로 확인하고 uvicorn을 껐다 켠다.
4. HTML의 연결 코드는 `scripts/apply_html_wiring.py`가 넣는다. 화면에 새 값 칸을 만들면 HTML에 숫자를 쓰지 말고 `—`로 두고 API로 채운다.

## 아직 API로 연결하지 않은 값

- 전국 어린이 보행사고 추이(2019~2025)와 사망 막대: 2019~2023은 국회예산정책처 자료, 2024~2025는 TAAS 내보내기가 필요하다.
- 과태료·범칙금 표와 막대: 도로교통법 시행령 별표 7·10 자료가 필요하다.
- 노인보호구역 개선안(정책 대안) 문단과 영상.

화면에 표시할 숫자를 바꾸려면 공식 원본과 정제 과정을 먼저 확인한다.

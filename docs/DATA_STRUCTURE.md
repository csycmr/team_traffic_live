# 데이터 흐름과 폴더 구조

화면의 통계값은 `공식 원자료 → 정제 CSV → app/services → JSON API → HTML 차트·카드` 순서로 연결한다.

## 폴더

| 위치 | 역할 |
| --- | --- |
| `data/raw/` | 내려받은 공식 원자료(TAAS xlsx, OECD 원본 CSV). 수정하지 않는다. |
| `data/*.csv`, `data/*.geojson`, `data/*.json` | 정제 결과. 번호(01~15)가 자료 종류다. |
| `scripts/clean_oecd_13.py`, `taas_accident_trend_2020_2025.ipynb` | 원자료를 정제 CSV로 만드는 코드 |
| `app/services/` | 정제 CSV를 읽어 값을 계산 (API가 아니라 함수) |
| `app/models.py` | API 응답 필드와 값 범위 |
| `app/main.py`, `app/flask_app.py` | 서비스 함수를 JSON으로 내보내는 얇은 라우트 |
| `tests/` | 서비스 값과 라우트 응답 검증 |

`data/` 안의 파일 위치는 README 링크, 화면 JavaScript, Flask의 `/data/<파일>` 경로가 직접 참조하므로 옮기지 않았다.

## API와 자료

| API | 서비스 | 자료 |
| --- | --- | --- |
| `GET /api/oecd/rankings` | `oecd_service.oecd_rankings` | `13_OECD_고령지표_wide.csv` |
| `GET /api/traffic/accident-trend` | `accident_service.accident_trend` | `15_TAAS_시도시군구_교통사고_2020-2025.csv` |
| `GET /api/traffic/national-deaths` | `accident_service.national_deaths` | `17_전국사망자_막대도넛.csv`(TAAS 합계와 대조) |
| `GET /api/traffic/child-pedestrian` | `accident_service.child_pedestrian` | `10_어린이보호구역_교통안전_요약.csv` (보행자 교통사고 · 서울 · 2025 · 12세 이하, 정확히 1행) |
| `GET /api/statistics/elderly` | `accident_service.elderly_pedestrian` | `01_자치구연도_패널.csv` (2025, 25개 자치구 합계) |
| `GET /api/cctv` | `cctv_service.seoul_cctv` | ITS API + `08_서울_자치구_경계.geojson` |
| `GET /api/citydata` | `citydata_service.citydata` | 서울시 도시데이터 API |

오류는 `ServiceError`로 올리고, 응답은 `{"error": 메시지}` 형태다.

## 정제 CSV 열

- `15_TAAS_시도시군구_교통사고_2020-2025.csv`: `연도, 시도, 시군구, 사고건수, 사망자수, 부상자수` (세로형, 2020~2025). 시군구가 `합계`인 행이 시도 합계, 시도가 `합계`인 행이 전국 합계. 전국 합계 행은 17개 시도 합계의 합보다 해마다 조금 크다(원본 특성). 추이 API는 전국 합계·서울 합계 행을 쓴다(2025: 193,889건 / 서울 34,309건·45,446명·212명).
- `10_어린이보호구역_교통안전_요약.csv`: `자료구분, 지역, 사고연도, 연령범위, 사고건수, 사망자수, 부상자수, 보호구역기록수, 자료기준일, 출처`

화면에 표시할 숫자를 바꾸려면 공식 원본과 정제 과정을 먼저 확인한다.

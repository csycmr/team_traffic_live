# 서울 교통안전 라이브

서울의 교통 상황을 시연하고, 노인·어린이 보행사고와 보호구역 현황을 한 화면에서 살펴보는 데이터 저널리즘 팀 프로젝트입니다.

**배포 사이트 (Railway)**

- [대시보드](https://flask-production-343483a0.up.railway.app/)
- [기자용 뉴스룸](https://flask-production-343483a0.up.railway.app/newsroom)

## 화면 구성

| 영역 | 내용 |
| --- | --- |
| 왼쪽 패널 | 교통사고, 사망·부상, 도로 소통, 평균 속도, CCTV 상태를 전광판으로 표시합니다. 전광판은 시연용 수치로 5초마다 갱신되며 일시정지할 수 있습니다. 기상·교통 상황도 시연용입니다. |
| 중앙 지도 | 카카오맵에서 서울 외곽선과 자치구 경계를 확인하고, 노인보호구역·어린이보호구역·사고다발지역을 각각 켜고 끌 수 있습니다. 핀을 누르면 상세 팝업이 열리고, 가장 최근에 누른 핀의 팝업이 앞에 표시됩니다. |
| 오른쪽 패널 | 2025년 서울 노인·어린이 보행사고 집계와 인구·보호구역 비교 그래프를 제공합니다. 그래프의 막대 높이는 비교 항목별 최댓값을 100%로 환산한 비율입니다. |

## 기자용 뉴스룸 (Flask · MySQL · AI)

대시보드 오른쪽 아래 **기사 작성** 버튼을 누르면 기자용 뉴스룸(`/newsroom`)으로 이동합니다. 뉴스룸의 **브리핑으로** 버튼을 이용해 대시보드로 돌아올 수 있습니다. 두 화면은 동일한 Flask 앱에서 제공됩니다.

| 단계 | 기자가 할 수 있는 일 | 구현 상태 |
| --- | --- | --- |
| ① 기사거리 추천 | 분석 지역·연도, 최근 보도 검색 조건, 키워드·참고 URL·취재 메모를 입력하고 AI 추천 후보를 비교한 뒤 선택한 기사거리만 DB에 저장 | 로컬 UI·API 연결 완료 |
| ② 기사 초안 | 저장된 기사거리를 선택하고 기자가 원하는 구성·강조점을 지침으로 입력하여 AI 초안 생성, 제목·본문 수정 및 MySQL 저장·재조회 | 로컬 UI·API 연결 완료 |
| ③ 자동 사실 검수 | 저장된 기사와 Fact Sheet·연결 근거를 대조하고 숫자·연도·출처·인과관계 표현의 문제를 확인, 수정 후 재검수 | 로컬 UI·API 연결 완료 |
| ④ 편집장 승인 | 검수 결과·기사 본문 확인, 4개 체크리스트와 편집장 인증을 거쳐 승인 또는 보류 | 로컬 UI·API 연결 완료 |
| ⑤ 승인 기사 | 승인·검수 통과 요건을 만족하는 기사만 목록 및 상세 화면에 표시하고 연결 근거 조회 | 로컬 UI·API 연결 완료 |

### 사실 검증과 편집 원칙

- 데이터의 계산 상태 `CHECKED`는 **내부 산식·집계 정합성 확인**을 뜻하며, 외부 자료 전체에 대한 독립적인 사실 검증을 뜻하지 않습니다.
- 보도 검색의 제목·링크·발행처 등 메타데이터는 그 자체로 기사의 검증된 원문 근거가 아닙니다. 기자가 입력한 취재 지침 역시 사실 근거로 자동 승격하지 않습니다.
- 고령 보행자 사고는 **사고 발생지 기준**, 고령인구는 **거주지 기준**이므로 인구 1만 명당 사고건수는 기술적 비교 지표이며 개인별 사고 위험률이나 정책 인과 효과로 해석하면 안 됩니다.
- AI 자동 검수 PASS는 최종 출고 승인과 다릅니다. 기사 수정 시 이전 검수 결과가 초기화되며, 편집장 승인에는 최신 검수 PASS·체크리스트·비밀번호 확인이 필요합니다.
- 검토대기 또는 보류된 기사는 승인 기사 조회 API에서 제외합니다.

### 실행 환경과 서비스 범위

로컬 Flask 서버를 실행한 뒤 [대시보드](http://127.0.0.1:5001/) 또는 [기자용 뉴스룸](http://127.0.0.1:5001/newsroom)에 접속합니다. 뉴스룸의 추천·초안 생성·검수·저장 기능에는 별도로 설정한 MySQL 연결 정보(`DATABASE_URL`) 및 AI 호출에 필요한 `OPENAI_API_KEY`가 사용됩니다. 편집장 결정 기능에는 서버 측 `EDITOR_PASSWORD_HASH` 설정이 필요합니다. 각 값은 비밀정보이므로 Git에 올리지 않습니다. AI 사용에는 API 요금이 발생할 수 있습니다.

기사 초안 생성 시 입력한 기자 지침은 `articles.reporter_guidance` 열에 저장합니다. **이 열을 로컬 MySQL에 추가한 이력은 Git 커밋만으로 팀원의 DB에 적용되지 않습니다.** 다른 환경에서는 해당 스키마 변경을 반영해야 합니다.

### Railway 배포

Flask 앱(대시보드 + 뉴스룸)은 Railway에 배포되어 있습니다: [https://flask-production-343483a0.up.railway.app/](https://flask-production-343483a0.up.railway.app/)

- 배포 환경의 `DATABASE_URL`, `OPENAI_API_KEY`, `EDITOR_PASSWORD_HASH` 등은 Railway 서비스의 Variables에서 설정합니다. 값은 Git·README·로그에 남기지 않습니다.
- `DATABASE_URL`은 `mysql+pymysql://` 형식이어야 합니다.
- 배포 DB와 로컬 DB는 별개일 수 있습니다. 로컬에서 바꾼 스키마는 배포 DB에 자동으로 반영되지 않으므로, 새 DB는 [newsroom_mysql_schema.sql](newsroom_mysql_schema.sql) 기준으로 구성하고 열이 추가되면 배포 DB에도 같은 변경을 적용합니다.
- 뉴스룸에서 "기존 초안을 불러오지 못했습니다" 같은 일반 오류가 보이면, Railway 서비스의 Deploy Logs에서 해당 문구로 검색해 실제 예외(테이블·열 누락, 접속 실패 등)를 먼저 확인합니다.

### 남은 작업 (백로그)

- 팀원이 함께 사용할 **공유 DB** 구성 및 배포 DB 스키마를 `newsroom_mysql_schema.sql`과 일치시키기
- 공개 환경에서의 접근 제어, 편집장 권한 보호, API 키·설정값 관리
- 배포된 주소에서 기사 추천 → 초안 → 검수 → 승인 → 조회의 실제 종단간 동작 확인

DB 이전은 **현 단계의 개발을 중단시키는 선행 작업이 아니라 후속 과제**로 관리합니다.

## 데이터와 기준

| 항목 | 기준과 자료 |
| --- | --- |
| 보행사고 | 2025년 서울 집계. 노인은 65세 이상, 어린이는 12세 이하입니다. [집계 자료](data/10_어린이보호구역_교통안전_요약.csv) |
| 인구 비교 | 2026년 9월 말 기준. 노인은 65세 이상, 어린이는 0~12세입니다. [서울 연령별 집계표](data/11_서울_연령별_주민등록인구_202609.csv) · [KOSIS 원자료](https://kosis.kr/statisticsList/mass/mass_list.jsp?org_id=101&tbl_id=DT_1B04006) |
| 보호구역 | 노인은 2025년 명단, 어린이는 전국어린이보호구역표준데이터의 서울 시설 기록을 사용합니다. [노인 명단](data/04_보호구역_마스터.csv) · [노인 위치](data/05_보호구역_경계.csv) · [어린이 기록](data/09_어린이보호구역_서울_지도용.csv) |
| 지도 경계·사고다발지역 | [서울시·자치구 경계 GeoJSON](data/08_서울_자치구_경계.geojson) · [2025년 사고다발지역 JSON](data/accident-hotspots-2025.json) |
| 어린이보호구역 지정 현황 | 경찰청 2026년 6월 30일 기준 서울 합계 [경찰청 지정현황](data/12_경찰청_어린이보호구역_지정현황_20260630.csv). 시설 목록은 기준일별로 [2025년 12월 31일](data/21_서울_어린이보호구역_지정현황_20251231_목록용.csv) · [2026년 6월 30일](data/22_서울_어린이보호구역_지정현황_20260630_목록용.csv) 파일을 씁니다. |
| 어린이 카메라 설치 전후 | 서울시 무인단속카메라 107대 설치 대상지의 전후 각 2년(2018~2019년, 2021~2022년) 집계. [전후 자료](data/20_서울_어린이보호구역_무인단속카메라_전후.csv) |
| 보호구역 개선 예산 | 서울시 2026년 예산서의 어린이·노인장애인 보호구역 개선 세부사업. 1곳당 환산액은 위 지정 목록의 구역 수로 나눕니다. [예산 CSV](data/14_서울시예산_2026.csv) |
| 전국 사망자·인구·OECD | [전국 사망자와 65세 이상 상태별 사망자](data/17_전국사망자_막대도넛.csv) · [전국 65세 이상 인구](data/18_전국_65세이상_주민등록인구.csv) · [OECD 고령자 사망률](data/13_OECD_고령지표_wide.csv) |

왼쪽 패널의 시연 수치와 오른쪽 패널의 자료 기반 집계도 구분해서 읽어주세요.

## Windows에서 로컬 실행

VS Code에서 저장소 폴더를 열고 PowerShell 터미널에서 진행합니다. Python 3.14가 필요합니다.

### 1. 가상환경 만들기와 패키지 설치

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`Successfully installed` 또는 `Requirement already satisfied`가 표시되면 설치가 끝난 상태입니다.

### 2. 서버 시작과 화면 확인

```powershell
.\.venv\Scripts\python.exe -m app.flask_app
```

터미널에 `Running on http://127.0.0.1:5001`이 보이면 [로컬 대시보드](http://127.0.0.1:5001/)를 엽니다. 로컬 카카오맵을 쓰려면 카카오 JavaScript SDK 허용 도메인에 `http://127.0.0.1:5001`을 등록해야 합니다. 서버 종료는 `Ctrl+C`입니다.

통계 API(FastAPI)는 두 번째 PowerShell 터미널에서 함께 실행합니다. 화면의 차트·카드가 이 서버의 값을 읽습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

`Uvicorn running on http://127.0.0.1:8000`이 보이면 [FastAPI 문서](http://127.0.0.1:8000/docs)에서 전체 API 목록과 응답 형태를 확인합니다. 자료나 서버 코드를 바꾼 뒤에는 `Ctrl+C`로 끄고 다시 실행해야 반영됩니다. 두 서버를 한 번에 띄우는 `scripts/run_windows.ps1`도 있습니다.

화면의 차트·카드 값은 이 API가 `data/`의 정제 CSV에서 계산해 줍니다. HTML에는 이 값들을 직접 적지 않고 `—`로 두며, API가 꺼져 있으면 `—`로 남습니다. 현재 HTML은 API 주소 `http://127.0.0.1:8000`을 직접 쓰므로, 서버를 다른 주소에 배포할 때는 이 주소를 바꿔야 합니다. API별 자료와 계산은 [데이터 흐름과 폴더 구조](docs/DATA_STRUCTURE.md)에 정리했습니다.

로컬에서 다른 카카오 JavaScript 키를 쓰려면 저장소 루트의 `.env`에 `KAKAO_MAP_JS_KEY=발급받은_JavaScript_키`를 추가하고 Flask를 재시작합니다. 해당 키의 JavaScript SDK 도메인에 브라우저에서 실제로 쓰는 주소를 등록합니다. 5001 포트라면 `http://127.0.0.1:5001`입니다.

### 3. CCTV 목록 API 확인

CCTV 목록까지 조회하려면 서버를 종료한 뒤 같은 PowerShell에서 아래 명령을 실행하고, 국가교통정보센터 CCTV 인증키를 입력합니다.

```powershell
$itsKey = Read-Host 'CCTV API 키' -AsSecureString
$itsCredential = [pscredential]::new('ITS', $itsKey)
$env:ITS_CCTV_API_KEY = $itsCredential.GetNetworkCredential().Password
Remove-Variable itsKey, itsCredential
.\.venv\Scripts\python.exe -m app.flask_app
```

[로컬 CCTV API](http://127.0.0.1:5001/api/cctv)를 열면 `source_count`(API 응답 건수), `seoul_count`(서울시 경계 안의 건수), `cameras`(이름·좌표·영상 주소 등)를 확인할 수 있습니다. 이 API는 Flask 서버에서 제공되며, 배포 환경에서는 Railway Variables에 `ITS_CCTV_API_KEY`가 설정되어 있어야 합니다. 전광판의 CCTV 상태는 시연용입니다.

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| [seoul-traffic-demo.html](seoul-traffic-demo.html) | 대시보드 화면과 지도 동작 |
| [app/main.py](app/main.py) | FastAPI 통계 API (OECD 순위, 교통사고 추이, 전국 사망자, 고령·어린이 보행사고, 보호구역 지도·현황, 사고다발지역, 개선 예산) |
| [app/flask_app.py](app/flask_app.py) | 대시보드 화면, 뉴스룸 API, CCTV·도시데이터 API를 제공하는 Flask 서버 |
| [app/services/](app/services/) | CSV를 읽어 값을 계산하는 서비스. Flask와 FastAPI가 함께 사용 |
| [app/adapters/](app/adapters/) | 국가교통정보센터·서울시 도시데이터 같은 외부 API 호출 |
| [app/models.py](app/models.py) | API 응답 형태(Pydantic) |
| [app/config.py](app/config.py) | `.env` 설정과 data 폴더 경로 |
| [newsroom/](newsroom/) | 뉴스룸 기사 초안·검수·추천 로직 |
| [tests/](tests/) | 서비스·API 테스트 |
| [docs/](docs/) | [데이터 흐름과 폴더 구조](docs/DATA_STRUCTURE.md), API 키 안내 |
| [scripts/](scripts/) | 실행·테스트 스크립트와 자료 정제 코드. `apply_html_wiring.py`는 화면 HTML에 API 연결 코드를 적용합니다(여러 번 실행해도 안전). |
| [make_child_zone_list.py](make_child_zone_list.py) | 어린이보호구역 지정현황 엑셀을 `21_`·`22_` 목록용 CSV로 바꿉니다. `openpyxl`이 필요합니다. |
| [newsroom_mysql_schema.sql](newsroom_mysql_schema.sql) | 뉴스룸 MySQL 8 스키마(`analysis_snapshots`, `story_ideas`, `articles`, `source_documents`, `article_evidence`) |
| [requirements.txt](requirements.txt) | 로컬 실행에 필요한 Python 패키지 |
| [assets/](assets/) | 배경 영상과 대표 이미지 |
| [data/](data/) | 교통사고·보호구역 분석 자료와 지도 경계 |

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

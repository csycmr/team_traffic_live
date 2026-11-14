# 서울 교통안전 라이브

서울의 교통 상황을 시연하고, 노인·어린이 보행사고와 보호구역 현황을 한 화면에서 살펴보는 데이터 저널리즘 팀 프로젝트입니다.

[서울 교통안전 라이브 열기](https://seoul-traffic-newsroom-z0ffv.beigemango7.chatgpt.site/)

## 화면 구성

| 영역 | 내용 |
| --- | --- |
| 왼쪽 패널 | 교통사고, 사망·부상, 도로 소통, 평균 속도, CCTV 상태를 전광판으로 표시합니다. 전광판은 시연용 수치로 5초마다 갱신되며 일시정지할 수 있습니다. 기상·교통 상황도 시연용입니다. |
| 중앙 지도 | 카카오맵에서 서울 외곽선과 자치구 경계를 확인하고, 노인보호구역·어린이보호구역·사고다발지역을 각각 켜고 끌 수 있습니다. 핀을 누르면 상세 팝업이 열리고, 가장 최근에 누른 핀의 팝업이 앞에 표시됩니다. |
| 오른쪽 패널 | 2025년 서울 노인·어린이 보행사고 집계와 인구·보호구역 비교 그래프를 제공합니다. 그래프의 막대 높이는 비교 항목별 최댓값을 100%로 환산한 비율입니다. |

## 데이터와 기준

| 항목 | 기준과 자료 |
| --- | --- |
| 보행사고 | 2025년 서울 집계. 노인은 65세 이상, 어린이는 12세 이하입니다. [집계 자료](data/10_어린이보호구역_교통안전_요약.csv) |
| 인구 비교 | 2026년 9월 말 기준. 노인은 65세 이상, 어린이는 0~14세입니다. [인구 출처](https://opus.ai.kr/semteo/region/population/seoul/) |
| 보호구역 | 노인은 2025년 명단, 어린이는 전국어린이보호구역표준데이터의 서울 시설 기록을 사용합니다. [노인 명단](data/04_보호구역_마스터.csv) · [노인 위치](data/05_보호구역_경계.csv) · [어린이 기록](data/09_어린이보호구역_서울.csv) |
| 지도 경계·사고다발지역 | [서울시·자치구 경계 GeoJSON](data/08_서울_자치구_경계.geojson) · [2025년 사고다발지역 JSON](data/accident-hotspots-2025.json) |

오른쪽 패널의 어린이 보행사고와 인구 비교는 연령 기준이 다릅니다. 왼쪽 패널의 시연 수치와 오른쪽 패널의 자료 기반 집계도 구분해서 읽어주세요.

## Windows에서 로컬 실행

VS Code에서 저장소 폴더를 열고 PowerShell 터미널에서 진행합니다. Python 3.14가 필요합니다.

### 1. 가상환경 만들기와 Flask 설치

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`Successfully installed` 또는 `Requirement already satisfied`가 표시되면 설치가 끝난 상태입니다.

### 2. 서버 시작과 화면 확인

```powershell
.\.venv\Scripts\python.exe app.py
```

터미널에 `Running on http://127.0.0.1:5000`이 보이면 [로컬 대시보드](http://127.0.0.1:5000/)를 엽니다. 로컬 카카오맵을 쓰려면 카카오 JavaScript SDK 허용 도메인에 `http://127.0.0.1:5000`을 등록해야 합니다. 서버 종료는 `Ctrl+C`입니다.

### 3. CCTV 목록 API 확인

CCTV 목록까지 조회하려면 서버를 종료한 뒤 같은 PowerShell에서 아래 명령을 실행하고, 국가교통정보센터 CCTV 인증키를 입력합니다.

```powershell
$itsKey = Read-Host 'CCTV API 키' -AsSecureString
$itsCredential = [pscredential]::new('ITS', $itsKey)
$env:ITS_CCTV_API_KEY = $itsCredential.GetNetworkCredential().Password
Remove-Variable itsKey, itsCredential
.\.venv\Scripts\python.exe app.py
```

[로컬 CCTV API](http://127.0.0.1:5000/api/cctv)를 열면 `source_count`(API 응답 건수), `seoul_count`(서울시 경계 안의 건수), `cameras`(이름·좌표·영상 주소 등)를 확인할 수 있습니다. 이 API는 로컬 Flask 서버에서 제공됩니다. 공개 사이트는 정적 페이지이며, 전광판의 CCTV 상태는 시연용입니다.

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| [seoul-traffic-demo.html](seoul-traffic-demo.html) | 대시보드 화면과 지도 동작 |
| [app.py](app.py) | 로컬 대시보드를 제공하고 CCTV 목록을 서울시 경계로 필터링 |
| [requirements.txt](requirements.txt) | 로컬 실행에 필요한 Python 패키지 |
| [assets/](assets/) | 배경 영상과 대표 이미지 |
| [data/](data/) | 교통사고·보호구역 분석 자료와 지도 경계 |

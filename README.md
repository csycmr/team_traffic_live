# 서울 교통안전 라이브

서울 교통 상황과 노인보호구역을 한 화면에 보여주는 팀 과제야. 왼쪽 전광판은 시연 데이터로 5초마다 갱신돼. 오른쪽 카카오맵에는 서울시 경계와 노인보호구역이 표시돼. 국가교통정보센터 CCTV 목록은 Flask의 `/api/cctv`로 조회할 수 있어. 지도 아이콘과 영상 재생은 연동 예정이야.

## 로컬 실행

Windows 11에서 VS Code로 저장소 폴더를 열고 PowerShell 터미널에서 진행해. Python 3.14가 필요해.

### 1. Flask 설치

저장소를 이미 내려받았다면 `git pull`로 최신 파일을 받아. 아래 명령은 한 줄씩 실행해.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt`에 적힌 Flask가 설치돼. `Successfully installed`가 표시되거나 이미 설치된 패키지라면 `Requirement already satisfied`가 표시돼.

### 2. CCTV 키 입력 및 서버 시작

같은 PowerShell에서 아래 블록을 붙여넣어. 키 입력창이 뜨면 국가교통정보센터의 **CCTV 인증키**를 입력해. 키는 현재 터미널에만 설정돼.

```powershell
$itsKey = Read-Host 'CCTV API 키' -AsSecureString
$itsCredential = [pscredential]::new('ITS', $itsKey)
$env:ITS_CCTV_API_KEY = $itsCredential.GetNetworkCredential().Password
Remove-Variable itsKey, itsCredential
.\.venv\Scripts\python.exe app.py
```

터미널에 `Running on http://127.0.0.1:5000`이 보이면 서버가 켜진 거야. 종료는 `Ctrl+C`를 눌러.

### 3. 브라우저에서 확인

| 주소 | 확인할 내용 |
|---|---|
| [대시보드](http://127.0.0.1:5000/) | 전광판과 지도 영역이 열려. 카카오맵 로컬 테스트에는 카카오 JavaScript SDK 도메인에 `http://127.0.0.1:5000`을 등록해야 해. |
| [CCTV API](http://127.0.0.1:5000/api/cctv) | `source_count`는 API에서 받은 건수, `seoul_count`는 서울시 경계 안에 있는 건수야. `cameras`에는 이름·좌표·영상 주소가 들어가. |

`ITS_CCTV_API_KEY` 설정 안내가 뜨면 키 입력과 서버 실행을 같은 터미널에서 했는지 확인해. `upstream_status`가 `401`이면 국가교통정보센터 CCTV 인증키를 확인해.

## 주요 파일

| 파일 | 역할 |
|---|---|
| `app.py` | 대시보드를 제공하고 CCTV 목록을 서울시 경계로 필터링 |
| `requirements.txt` | Python 패키지 설치 목록 |
| `seoul-traffic-demo.html` | 대시보드 화면 |
| `data/05_보호구역_경계.csv` | 보호구역 위치 자료 |
| `data/08_서울_자치구_경계.geojson` | 서울시와 자치구 경계 |

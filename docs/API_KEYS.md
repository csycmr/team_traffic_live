# API 키와 환경변수

`.env.example`을 `.env`로 복사해 채운다. `.env`는 Git에 올리지 않는다.

| 환경변수 | 용도 | 없을 때 |
| --- | --- | --- |
| `SEOUL_CITYDATA_API_KEY` | 서울시 실시간 도시데이터(`/api/citydata`) | 500 `서울시 API 인증키가 설정되지 않았어.` |
| `ITS_CCTV_API_KEY` | 국가교통정보센터 CCTV(`/api/cctv`) | 503 `ITS_CCTV_API_KEY 환경변수를 설정해 줘.` |
| `KAKAO_MAP_JS_KEY` | 로컬 카카오맵 JavaScript 키 | HTML에 적힌 기본 키 사용 |
| `DATA_DIR` | data 폴더 위치 (기본 `data`) | 저장소의 `data/` |
| `CORS_ORIGINS` | FastAPI가 허용할 화면 주소, 쉼표 구분 | `http://127.0.0.1:5001` |

통계 API(`/api/oecd/rankings`, `/api/traffic/*`, `/api/statistics/elderly`)는 키 없이 data 폴더의 CSV만 읽는다.

운영 배포에서는 화면 JavaScript의 `http://127.0.0.1:8000` 호출을 사용자 브라우저에서 접근 가능한 API 주소나 같은 출처 경로로 바꾸고, `CORS_ORIGINS`에 실제 화면 주소를 넣어야 한다.

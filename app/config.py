"""환경변수와 경로 설정. Flask와 FastAPI가 같은 설정을 쓴다."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class Settings(BaseModel):
    data_dir: Path = ROOT / "data"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5001"])
    flask_port: int = 5001
    fastapi_port: int = 8000

    kakao_map_js_key: str = ""
    its_cctv_api_key: str = ""
    seoul_citydata_api_key: str = ""
    citydata_cache_seconds: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("DATA_DIR") or "data").expanduser()
        origins = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]
        values = {
            "data_dir": data_dir if data_dir.is_absolute() else ROOT / data_dir,
            "kakao_map_js_key": os.getenv("KAKAO_MAP_JS_KEY", "").strip(),
            "its_cctv_api_key": os.getenv("ITS_CCTV_API_KEY", "").strip(),
            "seoul_citydata_api_key": os.getenv("SEOUL_CITYDATA_API_KEY", "").strip(),
        }
        if origins:
            values["cors_origins"] = origins
        return cls(**values)


def load_settings() -> Settings:
    """호출할 때마다 환경변수를 다시 읽는다. API 키처럼 실행 중 바뀔 수 있는 값에 쓴다."""
    return Settings.from_env()


@lru_cache
def get_settings() -> Settings:
    return load_settings()

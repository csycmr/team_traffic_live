"""기존 분석 저장소 데이터 경로 설정."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def processed_data_dir() -> Path:
    configured = os.getenv("DATA_DIR")
    if configured:
        location = Path(configured).expanduser()
        return location if location.is_absolute() else ROOT_DIR / location

    return ROOT_DIR / "data"

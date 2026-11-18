import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def real_data_dir() -> Path:
    return ROOT / "data"


@pytest.fixture
def write_csv(tmp_path):
    """작은 CSV를 임시 data 폴더에 만들어 돌려준다."""

    def _write(name: str, text: str) -> Path:
        (tmp_path / name).write_text(text.strip() + "\n", encoding="utf-8-sig")
        return tmp_path

    return _write

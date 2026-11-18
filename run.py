"""개발 서버 실행.

python run.py fastapi   # 통계 API, http://127.0.0.1:8000
python run.py flask     # 대시보드 화면, http://127.0.0.1:5001
"""

import sys

from app.config import load_settings


def main(target: str) -> None:
    settings = load_settings()
    if target == "fastapi":
        import uvicorn

        uvicorn.run("app.main:app", host="127.0.0.1", port=settings.fastapi_port)
    elif target == "flask":
        from app.flask_app import app

        app.run(host="127.0.0.1", port=settings.flask_port)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")

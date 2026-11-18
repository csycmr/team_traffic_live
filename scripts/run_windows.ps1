# 가상환경 준비 후 FastAPI(8000)와 Flask(5001)를 함께 실행한다.
# 실행: powershell -ExecutionPolicy Bypass -File .\scripts\run_windows.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3.14 -m venv .venv }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Start-Process powershell -ArgumentList '-NoExit', '-Command', ".\.venv\Scripts\python.exe run.py fastapi"
.\.venv\Scripts\python.exe run.py flask

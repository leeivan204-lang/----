@echo off
cd /d "%~dp0"
IF EXIST ".venv\Scripts\uvicorn.exe" (
    ".venv\Scripts\uvicorn.exe" main:app --reload --host 127.0.0.1 --port 8000
) ELSE (
    echo Virtual environment not found or uvicorn missing.
    exit /b 1
)

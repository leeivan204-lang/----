@echo off
cd /d "%~dp0"
echo Starting Work Log Assistant with Auth...
py -m uv run uvicorn main:app --reload --host 127.0.0.1 --port 8001
pause

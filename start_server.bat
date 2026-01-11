@echo off
echo Starting Case Log Assistant Server...

:: 嘗試偵測 Python 指令
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set PY_CMD=py
    ) else (
        echo Error: Python not found. Please install Python.
        pause
        exit /b
    )
)

echo Using Python command: %PY_CMD%

echo Installing dependencies...
%PY_CMD% -m pip install -r requirements.txt

echo.
echo Starting Server at http://localhost:8000
echo.
%PY_CMD% main.py
pause

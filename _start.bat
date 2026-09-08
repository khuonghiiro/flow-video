@echo off
title Google Flow Kit - Khoi Chay He Thong
color 0A
cls

echo ==============================================================================
echo                   GOOGLE FLOW KIT - KHOI CHAY HE THONG
echo ==============================================================================
echo.

set "CURRENT_DIR=%~dp0"
if "%CURRENT_DIR:~-1%"=="\" set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"

if exist "%CURRENT_DIR%\agent-veo3" (
    set "ROOT_DIR=%CURRENT_DIR%"
    set "AGENT_DIR=%CURRENT_DIR%\agent-veo3"
) else (
    set "AGENT_DIR=%CURRENT_DIR%"
    set "ROOT_DIR=%CURRENT_DIR%\.."
)

set "VENV_PY=%AGENT_DIR%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
        set "VENV_PY=%ROOT_DIR%\.venv\Scripts\python.exe"
    )
)

echo [1/3] Kiem tra moi truong ao Python...
if not exist "%VENV_PY%" (
    color 0C
    echo [LOI] Chua tim thay moi truong ao .venv!
    echo Vui long chay file _setup_env.bat truoc de cai dat moi truong.
    echo.
    pause
    exit /b 1
)

echo [2/3] Khoi dong Dashboard UI (tu FlowKit core)...
if exist "%ROOT_DIR%\flowkit\dashboard\package.json" (
    start "FlowKit Dashboard UI" cmd /k "cd /d "%ROOT_DIR%\flowkit\dashboard" && npm.cmd run dev"
    echo - Da mo tien trinh Dashboard UI tu FlowKit core.
) else if exist "%ROOT_DIR%\dashboard\package.json" (
    start "FlowKit Dashboard UI" cmd /k "cd /d "%ROOT_DIR%\dashboard" && npm.cmd run dev"
    echo - Da mo tien trinh Dashboard UI.
) else if exist "%AGENT_DIR%\dashboard\package.json" (
    start "FlowKit Dashboard UI" cmd /k "cd /d "%AGENT_DIR%\dashboard" && npm.cmd run dev"
    echo - Da mo tien trinh Dashboard UI.
) else (
    echo - Khong tim thay thu muc Dashboard UI. Bo qua buoc nay.
)

echo.
echo [3/3] Khoi dong Flow Kit Agent Backend Server (Port 8100)...
echo ==============================================================================
echo    Backend API: http://127.0.0.1:8100/
echo    API Docs:    http://127.0.0.1:8100/docs
echo    Healthcheck: http://127.0.0.1:8100/health
echo ==============================================================================
echo.

timeout /t 2 /nobreak >nul 2>nul || ping 127.0.0.1 -n 3 >nul
start "" "http://127.0.0.1:8100/health"

cd /d "%AGENT_DIR%"
"%VENV_PY%" -m uvicorn agent.main:app --host 127.0.0.1 --port 8100 --reload

pause

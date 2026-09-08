@echo off
title Google Flow Kit - Khoi Chay He Thong
color 0A
cls

echo ==============================================================================
echo                   GOOGLE FLOW KIT - KHOI CHAY HE THONG
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [1/3] Kiem tra moi truong ao Python...
if not exist ".venv\Scripts\python.exe" (
    color 0C
    echo [LOI] Chua tim thay moi truong ao .venv!
    echo Vui long chay file _install_flowkit_env.bat truoc de cai dat moi truong.
    echo.
    pause
    exit /b 1
)

echo [2/3] Khoi dong Dashboard UI (tu FlowKit core)...
if exist "..\flowkit\dashboard\package.json" (
    start "FlowKit Dashboard UI" cmd /k "cd /d "%~dp0..\flowkit\dashboard" && npm.cmd run dev"
    echo - Da mo tien trinh Dashboard UI tu FlowKit core.
) else if exist "dashboard\package.json" (
    start "FlowKit Dashboard UI" cmd /k "cd /d "%~dp0dashboard" && npm.cmd run dev"
    echo - Da mo tien trinh Dashboard UI.
)

echo [3/3] Khoi dong Flow Kit Agent Backend Server (Port 8100)...
echo ==============================================================================
echo    Backend API: http://127.0.0.1:8100/
echo    API Docs:    http://127.0.0.1:8100/docs
echo    Healthcheck: http://127.0.0.1:8100/health
echo ==============================================================================
echo.

timeout /t 2 >nul
start "" "http://127.0.0.1:8100/health"

.venv\Scripts\python.exe -m uvicorn agent.main:app --host 127.0.0.1 --port 8100 --reload

pause

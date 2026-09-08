@echo off
title Google Flow Kit - Cai Dat Moi Truong
color 0B
cls

echo ==============================================================================
echo                   GOOGLE FLOW KIT - CAI DAT MOI TRUONG
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

set "VENV_DIR=%AGENT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo [1/4] Kiem tra Python 3...
where python >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [LOI] Khong tim thay Python tren may tinh!
    echo Vui long cai dat Python 3.10+ tu https://www.python.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo - Python: %PY_VER%
echo.

echo [2/4] Thiet lap moi truong ao Python (.venv)...
if not exist "%VENV_DIR%" (
    echo - Dang tao moi truong ao .venv tai %VENV_DIR%...
    python -m venv "%VENV_DIR%"
) else (
    echo - Moi truong ao .venv da ton tai tai %VENV_DIR%.
)

echo - Dang cai dat thu vien Python tu requirements.txt...
call "%VENV_PY%" -m pip install --upgrade pip

if exist "%AGENT_DIR%\requirements.txt" (
    echo - Dang cai dat dependencies cho Agent Veo3...
    call "%VENV_PY%" -m pip install -r "%AGENT_DIR%\requirements.txt"
)
if %errorlevel% neq 0 (
    color 0C
    echo [LOI] Cai dat requirements.txt gap loi!
    pause
    exit /b 1
)
echo - Da cai dat xong thu vien Python Backend!
echo.

echo [3/4] Cai dat thu vien Dashboard Frontend (npm install)...
where node >nul 2>nul
if %errorlevel% neq 0 (
    color 0E
    echo [CANH BAO] Khong tim thay Node.js. Bo qua buoc cai dat Dashboard UI.
) else (
    set NODE_OPTIONS=--dns-result-order=ipv4first
    if exist "%ROOT_DIR%\flowkit\dashboard\package.json" (
        cd /d "%ROOT_DIR%\flowkit\dashboard"
        echo - Dang chay npm install trong flowkit\dashboard...
        call npm.cmd install --no-audit --no-fund
        cd /d "%CURRENT_DIR%"
        echo - Da cai dat xong thu vien Dashboard UI trong flowkit!
    ) else if exist "%ROOT_DIR%\dashboard\package.json" (
        cd /d "%ROOT_DIR%\dashboard"
        echo - Dang chay npm install trong thu muc dashboard...
        call npm.cmd install --no-audit --no-fund
        cd /d "%CURRENT_DIR%"
        echo - Da cai dat xong thu vien Dashboard UI!
    ) else if exist "%AGENT_DIR%\dashboard\package.json" (
        cd /d "%AGENT_DIR%\dashboard"
        echo - Dang chay npm install trong thu muc agent-veo3\dashboard...
        call npm.cmd install --no-audit --no-fund
        cd /d "%CURRENT_DIR%"
        echo - Da cai dat xong thu vien Dashboard UI!
    )
)
echo.

echo [4/4] Dong bo hoa cau hinh Agent Skill...
if exist "%ROOT_DIR%\flowkit\setup.py" (
    cd /d "%ROOT_DIR%\flowkit"
    call "%VENV_PY%" setup.py --tool gemini
    cd /d "%CURRENT_DIR%"
) else if exist "%AGENT_DIR%\setup.py" (
    cd /d "%AGENT_DIR%"
    call "%VENV_PY%" setup.py --tool gemini
    cd /d "%CURRENT_DIR%"
) else (
    echo - Khong tim thay file setup.py. Bo qua buoc nay.
)

echo.
echo ==============================================================================
echo     CAI DAT FLOW KIT HOAN TAT! HAY CHAY _start.bat DE KHOI DONG.
echo ==============================================================================
echo.
pause

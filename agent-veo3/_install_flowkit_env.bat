@echo off
title Google Flow Kit - Cai Dat Moi Truong
color 0B
cls

echo ==============================================================================
echo                   GOOGLE FLOW KIT - CAI DAT MOI TRUONG
echo ==============================================================================
echo.

cd /d "%~dp0"

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
if not exist ".venv" (
    echo - Dang tao moi truong ao .venv...
    python -m venv .venv
) else (
    echo - Moi truong ao .venv da ton tai.
)

echo - Dang cai dat thu vien Python tu requirements.txt...
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt
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
    if exist "..\flowkit\dashboard\package.json" (
        cd ..\flowkit\dashboard
        echo - Dang chay npm install trong ..\flowkit\dashboard...
        call npm.cmd install --no-audit --no-fund
        cd "%~dp0"
        echo - Da cai dat xong thu vien Dashboard UI trong flowkit!
    ) else if exist "dashboard\package.json" (
        cd dashboard
        echo - Dang chay npm install trong thu muc dashboard...
        call npm.cmd install --no-audit --no-fund
        cd "%~dp0"
        echo - Da cai dat xong thu vien Dashboard UI!
    )
)
echo.

echo [4/4] Dong bo hoa cau hinh Agent Skill...
if exist ".venv\Scripts\python.exe" (
    call .venv\Scripts\python.exe setup.py --tool gemini
) else (
    python setup.py --tool gemini
)

echo.
echo ==============================================================================
echo     CAI DAT FLOW KIT HOAN TAT! HAY CHAY _start_flowkit.bat DE KHOI DONG.
echo ==============================================================================
echo.
pause

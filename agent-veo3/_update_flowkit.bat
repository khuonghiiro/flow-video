@echo off
title Google Flow Kit - Dong Bo Cap Nhat Tu Tac Gia (Upstream Update)
color 0B
cls

echo ==============================================================================
echo       GOOGLE FLOW KIT - DONG BO CAP NHAT TU TAC GIA (UPSTREAM UPDATE)
echo ==============================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\sync_flowkit.py
) else (
    python scripts\sync_flowkit.py
)

echo.
pause

@echo off
title Sortling Discord Bot launcher
echo ============================================================
echo   STARTING SORTLING DISCORD BOT (Sortling V1)
echo ============================================================
echo.

set PYTHONPATH=.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. 
    echo Please make sure .venv folder exists in this directory.
    echo.
    pause
    exit /b 1
)

echo Initializing database and starting bot...
.venv\Scripts\python.exe main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Bot stopped with exit code %ERRORLEVEL%.
    pause
)

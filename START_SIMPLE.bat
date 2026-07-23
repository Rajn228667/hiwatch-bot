@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PIERCE BOT FAST - DO NOT CLOSE

echo ========================================
echo  HiWatch bot FAST
echo  Do not close this window
echo ========================================

if not exist ".env" (
  echo No .env file!
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  if exist .venv\Scripts\python.exe (
    set "PY=.venv\Scripts\python.exe"
  ) else (
    set "PY=python"
  )
) else (
  set "PY=python"
)

:loop
echo [%time%] starting...
"%PY%" -u simple_bot.py
echo [%time%] exit %ERRORLEVEL% - restart 2s
timeout /t 2 /nobreak >nul
goto loop

@echo off
chcp 65001 >nul
cd /d "%~dp0"
title HiWatch Settings Bot (Пирс)

echo ================================
echo  HiWatch Settings Bot
echo  НЕ ЗАКРЫВАЙ это окно!
echo ================================

if not exist ".env" (
  echo [!] Нет .env — копирую пример
  if exist ".env.example" copy /Y ".env.example" ".env" >nul
  echo Открой .env и вставь BOT_TOKEN
  notepad ".env"
  pause
  exit /b 1
)

findstr /R /C:"^BOT_TOKEN=.\+" ".env" >nul
if errorlevel 1 (
  echo [!] BOT_TOKEN пустой в .env
  notepad ".env"
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Создаю venv...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

:loop
echo.
echo [%date% %time%] Запуск бота...
python -u -m bot.main
echo.
echo [!] Бот остановился (код %ERRORLEVEL%). Перезапуск через 3 сек...
timeout /t 3 /nobreak >nul
goto loop

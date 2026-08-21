@echo off
title 17-0 NFL Draft Discord Bot
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)
python run_bot.py
pause

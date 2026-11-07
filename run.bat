@echo off
chcp 65001 >nul
cd /d "%~dp0"
title turbo.py
python turbo.py config.json
echo.
echo Скрипт завершён.
pause

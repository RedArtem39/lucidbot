@echo off
chcp 65001 >nul
title LucidBot — Installer & Setup Wizard
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден в системе. Пожалуйста, установите Python 3.10+ с галочкой 'Add to PATH'.
    pause
    exit /b 1
)

python setup.py
pause

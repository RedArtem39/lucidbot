@echo off
chcp 65001 >nul
title LucidBot — AI Companion & Roleplay Platform
cd /d "%~dp0"

echo [LucidBot] Запуск платформы AI-персонажей...
"C:\Users\User\Desktop\SDBot\venv\Scripts\python.exe" main.py
pause

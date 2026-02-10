@echo off
cd /d "%~dp0"
echo Iniciando V-Strike Bot...
echo Por favor, asegura que tienes INTERNET (y VPN si estas en Venezuela).
.\.venv\Scripts\python.exe bot.py
pause

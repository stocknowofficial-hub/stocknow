@echo off
chcp 65001 >nul
set LOG_DIR=%~dp0..\logs\cloudflare
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=1-3 delims=/" %%a in ("%date%") do set TODAY=%%c-%%a-%%b
set LOG_FILE=%LOG_DIR%\%TODAY%.log

echo 📡 Cloudflare 로그 수집 시작: %LOG_FILE%
echo 시작: %date% %time% >> "%LOG_FILE%"

npx wrangler pages deployment tail --project-name stock-now --environment production --format pretty >> "%LOG_FILE%" 2>&1

@echo off
rem Start the dashboard (if not already running) and open it in the browser.
cd /d "%~dp0"
set PORT=8765
for /f "tokens=2 delims==" %%p in ('findstr /b "DASHBOARD_PORT=" .env 2^>nul') do set PORT=%%p
set URL=http://127.0.0.1:%PORT%
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing '%URL%/api/run-status' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
  start "" "%URL%"
  exit /b
)
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start "" %URL%"
".venv\Scripts\python.exe" -m dashboard.app

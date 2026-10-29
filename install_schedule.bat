@echo off
rem Creates the Windows scheduled tasks for the Internship Job Agent (current user, no admin needed).
cd /d "%~dp0"
set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
echo Creating "JobAgent 0800" and "JobAgent 1800" (pipeline, daily)...
schtasks /Create /TN "JobAgent 0800" /TR "\"%ROOT%\run_pipeline.bat\"" /SC DAILY /ST 08:00 /F
schtasks /Create /TN "JobAgent 1800" /TR "\"%ROOT%\run_pipeline.bat\"" /SC DAILY /ST 18:00 /F
echo Creating "JobAgent Dashboard" (starts hidden at logon)...
schtasks /Create /TN "JobAgent Dashboard" /SC ONLOGON /TR "\"%ROOT%\.venv\Scripts\pythonw.exe\" \"%ROOT%\serve_dashboard.pyw\"" /F
echo Starting the dashboard now...
schtasks /Run /TN "JobAgent Dashboard"
echo.
schtasks /Query /FO TABLE /TN "JobAgent 0800"
schtasks /Query /FO TABLE /TN "JobAgent 1800"
schtasks /Query /FO TABLE /TN "JobAgent Dashboard"
echo.
echo Done. Dashboard: http://127.0.0.1:8765
pause

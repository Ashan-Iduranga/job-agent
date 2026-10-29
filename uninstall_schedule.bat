@echo off
rem Removes the Internship Job Agent scheduled tasks.
schtasks /Delete /TN "JobAgent 0800" /F
schtasks /Delete /TN "JobAgent 1800" /F
schtasks /Delete /TN "JobAgent Dashboard" /F
echo Done.
pause

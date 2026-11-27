@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
"C:\Python313\python.exe" -m tada_ci.run_newsjacking >> "%~dp0logs\newsjacking.log" 2>&1

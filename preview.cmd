@echo off
setlocal
cd /d "%~dp0"
set "probe=import sys; sys.exit(sys.version_info[:2] < (3, 10))"
set "runner=py -3"
%runner% -c "%probe%" >nul 2>&1
if not errorlevel 1 goto run
set "runner=python"
%runner% -c "%probe%" >nul 2>&1
if not errorlevel 1 goto run

echo [Python not found] Neither py -3 nor python could run Python 3.10 or newer.
echo Install Python 3.10+ from https://www.python.org/downloads/windows/ and reopen preview.cmd.
pause
exit /b 1

:run
%runner% -c "import sys; print('[Python OK]', sys.version.split()[0], sys.executable)"
%runner% "%~dp0preview_portfolio.py"
if not errorlevel 1 exit /b 0
echo [Preview error] Python was found. Please copy the error lines immediately above this message.
pause
exit /b 1

@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    echo Please install Python and try again.
    pause
    exit /b 1
)

echo Starting SP News Update Admin...
echo Open http://127.0.0.1:8000/ in your browser.
python admin.py

pause

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

python main.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
    echo Run completed. Please check the logs folder for details.
) else (
    echo Run failed. Please check the message above and the logs folder.
)

pause
exit /b %EXIT_CODE%

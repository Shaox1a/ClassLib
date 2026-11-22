@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1" %*
if errorlevel 1 (
    echo Local startup failed. See the error above.
    pause
    exit /b 1
)

@echo off
setlocal
echo ===================================================
echo   17-0 NFL Bot - Syncing All Updates to GitHub...
echo ===================================================

set "GIT_EXE=%LOCALAPPDATA%\GitHubDesktop\app-3.6.4\resources\app\git\cmd\git.exe"
if not exist "%GIT_EXE%" (
    for /d %%i in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do (
        if exist "%%i\resources\app\git\cmd\git.exe" set "GIT_EXE=%%i\resources\app\git\cmd\git.exe"
    )
)

"%GIT_EXE%" add .
"%GIT_EXE%" commit -m "Update 17-0 bot, activity, and rules"
"%GIT_EXE%" push -u origin main --force

echo.
echo ===================================================
echo   Done! Changes pushed to GitHub and Railway!
echo ===================================================
pause

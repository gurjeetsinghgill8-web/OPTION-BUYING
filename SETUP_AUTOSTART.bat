@echo off
chcp 65001 >nul
title BHARAT FUTURES - AUTO RESTART SETUP
color 0B

echo ============================================================
echo   BHARAT FUTURES - WINDOWS AUTO START SETUP
echo   Bot will restart automatically when laptop starts
echo ============================================================
echo.

set BOT_BAT=C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\RUN_BOT.bat
set DASH_BAT=C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE\RUN_DASHBOARD.bat

echo [1/2] Setting up Bot to auto-start on Windows login...
schtasks /create /tn "BharatFuturesBot" /tr "\"%BOT_BAT%\"" /sc onlogon /rl highest /f
if %ERRORLEVEL%==0 (
    echo   Bot auto-start: DONE
) else (
    echo   Bot auto-start: Check admin rights
)

echo.
echo [2/2] Setting up Dashboard to auto-start on Windows login...
schtasks /create /tn "BharatFuturesDash" /tr "\"%DASH_BAT%\"" /sc onlogon /rl highest /f
if %ERRORLEVEL%==0 (
    echo   Dashboard auto-start: DONE
) else (
    echo   Dashboard auto-start: Check admin rights
)

echo.
echo ============================================================
echo   AUTO-START SETUP COMPLETE!
echo.
echo   Now: Keep laptop ON and plugged in
echo   Laptop restart/sleep pe bhi bot auto-restart hoga!
echo   Dashboard: http://localhost:8600
echo ============================================================
echo.
pause

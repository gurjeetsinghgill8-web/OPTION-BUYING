@echo off
chcp 65001 >nul
title BHARAT FUTURES ENGINE - RUNNING
color 0A

echo.
echo  ============================================================
echo    BHARAT FUTURES ENGINE v2.0 - STARTING
echo  ============================================================
echo.

cd /d "%~dp0"

REM Check secrets.txt
findstr "APNI_API_KEY" secrets.txt >nul 2>&1
if %ERRORLEVEL%==0 (
    echo  ERROR: secrets.txt fill nahi ki!
    echo  Pehle SETUP.bat chalao aur API keys daalo.
    echo.
    notepad secrets.txt
    pause
    exit
)

echo  Starting Trading Bot...
start "BHARAT BOT" cmd /k "chcp 65001 & python main.py"

timeout /t 3 >nul

echo  Starting Dashboard...
start "BHARAT DASHBOARD" cmd /k "chcp 65001 & python -m streamlit run app.py --server.port 8600"

timeout /t 4 >nul

echo  Opening Dashboard in browser...
start http://localhost:8600

echo.
echo  ============================================================
echo    BOT + DASHBOARD STARTED!
echo    Dashboard: http://localhost:8600
echo    Dono windows band mat karna!
echo  ============================================================
echo.
pause

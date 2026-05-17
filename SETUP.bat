@echo off
chcp 65001 >nul
title BHARAT FUTURES ENGINE - SETUP
color 0A

echo.
echo  ============================================================
echo    BHARAT FUTURES ENGINE v2.0 - FIRST TIME SETUP
echo    BTC Perpetual Futures - SuperTrend Algorithm
echo  ============================================================
echo.
echo  [1/4] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Python nahi mila! Please install:
    echo  https://www.python.org/downloads/
    echo  "Add to PATH" zaroor tick karna!
    start https://www.python.org/downloads/
    pause
    exit
)
echo  Python: OK

echo.
echo  [2/4] Installing required packages...
pip install streamlit requests pandas numpy --quiet
echo  Packages: OK

echo.
echo  [3/4] Setting up secrets file...
if not exist "secrets.txt" (
    copy "secrets_TEMPLATE.txt" "secrets.txt"
    echo  secrets.txt created!
)

echo.
echo  [4/4] Opening secrets.txt - Fill your API keys!
notepad secrets.txt

echo.
echo  ============================================================
echo    SETUP COMPLETE! Ab RUN_ALL.bat chalao!
echo  ============================================================
pause

@echo off
title BHARAT FUTURES — UPLOAD TO VPS
color 0E
chcp 65001 >nul

echo ============================================================
echo   BHARAT FUTURES ENGINE — UPLOAD TO VPS (HostIndia)
echo ============================================================
echo.

REM ===== FILL THESE =====
set VPS_IP=157.49.187.4
set VPS_USER=root
REM =====================

set LOCAL_FOLDER=C:\Users\pc\Desktop\gurjas ai\BHARAT-FUTURES-ENGINE
set REMOTE_FOLDER=/root/bharat-futures-engine

echo [1/3] Uploading all files to VPS...
echo.
echo Using SCP to upload files to %VPS_USER%@%VPS_IP%:%REMOTE_FOLDER%
echo.

scp -r "%LOCAL_FOLDER%\*" %VPS_USER%@%VPS_IP%:%REMOTE_FOLDER%/

echo.
echo [2/3] Files uploaded!
echo.
echo [3/3] Now SSH into VPS and run:
echo.
echo   ssh %VPS_USER%@%VPS_IP%
echo   cd %REMOTE_FOLDER%
echo   chmod +x deploy_vps.sh
echo   bash deploy_vps.sh
echo.
echo ============================================================
echo   After deploy, dashboard will be at:
echo   http://%VPS_IP%:8600
echo ============================================================
echo.
pause

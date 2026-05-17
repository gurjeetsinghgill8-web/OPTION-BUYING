@echo off
echo ==========================================
echo   BITCOIN OPTIONS ENGINE — Dashboard
echo ==========================================
cd /d "%~dp0"
streamlit run app.py --server.port 8501
pause

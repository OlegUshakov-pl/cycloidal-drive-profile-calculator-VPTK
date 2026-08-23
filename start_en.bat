@echo off
cd /d "%~dp0"
call ..\venv\Scripts\activate.bat
streamlit run app_en.py --server.port 8502
pause
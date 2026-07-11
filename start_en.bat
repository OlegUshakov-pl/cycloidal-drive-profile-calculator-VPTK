@echo off
cd /d "%~dp0"
call ".\venv\Scripts\python.exe" -m streamlit run app_en.py --server.port 8502
pause

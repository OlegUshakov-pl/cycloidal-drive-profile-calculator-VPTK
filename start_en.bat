@echo off
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m streamlit run app_en.py --server.port 8502
pause
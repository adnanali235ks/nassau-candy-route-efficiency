@echo off
rem Starts the dashboard with THIS project's virtual environment (.venv), never a global or temporary Python.
rem Extra arguments are passed to Streamlit, e.g.:  run_app.bat --server.port 8502
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo The project virtual environment was not found: %PY%
  echo Run setup_env.bat first.
  exit /b 1
)

"%PY%" -c "import streamlit, pandas, numpy, plotly, ortools, openpyxl, reportlab" 2>nul
if errorlevel 1 (
  echo A required package is missing from the project environment: %PY%
  echo Run setup_env.bat to install requirements.txt into that environment.
  exit /b 1
)

echo Starting the dashboard with: %PY%
"%PY%" -m streamlit run app.py %*

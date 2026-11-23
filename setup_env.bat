@echo off
rem Creates the project's virtual environment (.venv) if needed and installs requirements.txt INTO IT.
rem Every pip command uses .venv\Scripts\python.exe, so nothing is installed into a global or temporary Python.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating the project virtual environment in %~dp0.venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create .venv. Is Python installed and on PATH?
    exit /b 1
  )
)

echo Installing requirements into %~dp0.venv ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed.
  exit /b 1
)

echo.
echo Done. Start the dashboard with run_app.bat

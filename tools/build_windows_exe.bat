@echo off
setlocal

if not exist .venv (
  echo .venv not found. Create the virtual environment first.
  exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 exit /b 1

python -m pip install -e .[build]
if errorlevel 1 exit /b 1

pyinstaller --clean suki_helper.spec
if errorlevel 1 exit /b 1

echo Build complete: dist\suki-helper.exe

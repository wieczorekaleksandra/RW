@echo off
setlocal enabledelayedexpansion
set "PYTHON_PATH=C:\Users\grzes\AppData\Local\Programs\Python\Python312"
set "PATH=!PYTHON_PATH!;!PYTHON_PATH!\Scripts;!PATH!"
cd /d "%~dp0"
python -m src.main --gui
pause

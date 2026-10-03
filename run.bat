@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0harvester.py" %*
) else (
  python "%~dp0harvester.py" %*
)

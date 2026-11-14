@echo off
cd /d "%~dp0"
rem Abre numa janela de consola classica (conhost): e la que o icone do elemental aparece na barra de tarefas.
if not defined ELEM_HOST (set "ELEM_HOST=1" & start "Elementais do Fortnite" conhost.exe cmd /c ""%~f0" %*" & exit /b)
where python >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado. Instala o Python 3 em python.org e marca "Add python.exe to PATH".
  pause
  exit /b 1
)
python -c "import cv2, mss, numpy" >nul 2>&1
if errorlevel 1 (
  echo A instalar o que falta, so da primeira vez...
  python -m pip install -r requirements.txt
)
python iniciar.py %*
if errorlevel 1 pause

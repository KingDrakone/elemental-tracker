@echo off
cd /d "%~dp0"
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
python -c "import webview" >nul 2>&1
if errorlevel 1 if not exist .sem_webview (
  echo A instalar a janela do programa, so da primeira vez...
  python -m pip install pywebview
  python -c "import webview" >nul 2>&1
  if errorlevel 1 echo x> .sem_webview
)
where pythonw >nul 2>&1
if errorlevel 1 (
  start "" python iniciar.py --sem-consola
) else (
  start "" pythonw iniciar.py --sem-consola
)

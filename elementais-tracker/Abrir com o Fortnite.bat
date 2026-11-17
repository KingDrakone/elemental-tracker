@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado. Instala o Python 3 em python.org e marca "Add python.exe to PATH".
  pause
  exit /b 1
)
set "PASTA=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "V=%PASTA%\Elementais Vigia.vbs"
del "%PASTA%\Elementais Vigia.lnk" >nul 2>&1
echo Set s=CreateObject("WScript.Shell") > "%V%"
echo s.CurrentDirectory="%~dp0" >> "%V%"
echo s.Run "python ""%~dp0vigiar.pyw""", 0, False >> "%V%"
if not exist "%V%" (
  echo Nao consegui ativar: nao deu para escrever na pasta de arranque.
  pause
  exit /b 1
)
del vigia.log >nul 2>&1
start "" wscript "%V%"
echo A ligar o vigia...
timeout /t 5 /nobreak >nul
if exist vigia.log (
  echo.
  echo ATIVO - o vigia esta a correr:
  type vigia.log
  echo.
  echo O painel dos Elementais abre sozinho quando o Fortnite abrir ^(e quando ligares o PC^).
  echo Para desativar: "Nao abrir com o Fortnite.bat".
) else (
  echo.
  echo O vigia NAO arrancou. Faz duplo clique em "Ver vigia.bat" e diz-me o que aparece.
)
pause

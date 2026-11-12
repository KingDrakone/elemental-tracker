@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\Elementais do Fortnite.lnk'); $s.TargetPath='%~dp0iniciar.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0icone.ico'; $s.Save()"
if errorlevel 1 (echo Nao consegui criar o atalho.) else (echo Atalho "Elementais do Fortnite" criado no ambiente de trabalho, com o icone do elemental.)
pause

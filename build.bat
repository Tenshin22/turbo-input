@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Сборка TurboInput.exe...
python -m pip install --quiet --upgrade pyinstaller
python -m PyInstaller --noconfirm --onefile --noconsole --name TurboInput ^
  --icon icon.ico ^
  --add-binary "ViGEmClient.dll;." ^
  --distpath dist --workpath build app.py
if errorlevel 1 goto fail
copy /y dist\TurboInput.exe . >nul
echo.
echo Готово: %~dp0TurboInput.exe
pause
exit /b 0
:fail
echo Сборка не удалась.
pause
exit /b 1

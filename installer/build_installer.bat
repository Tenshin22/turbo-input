@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Сборка установщика Turbo Input.
rem Компилятор Inno Setup 7 ищется в стандартных местах или рядом (..\..\tools).

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe
if exist "E:\Agent_projct\tools\innosetup\IS7\ISCC.exe" set ISCC=E:\Agent_projct\tools\innosetup\IS7\ISCC.exe

if "%ISCC%"=="" (
  echo Inno Setup не найден. Скачай с https://jrsoftware.org/isdl.php и установи.
  pause
  exit /b 1
)

echo Компилятор: %ISCC%
"%ISCC%" installer.iss
if errorlevel 1 (
  echo Сборка установщика не удалась.
  pause
  exit /b 1
)
echo.
echo Готово: %~dp0..\TurboInput_Setup.exe
pause
exit /b 0

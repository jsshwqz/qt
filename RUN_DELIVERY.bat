@echo off
setlocal

set "ROOT=%~dp0"
set "REL=%ROOT%QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\QtScrcpy.exe"
set "BUILD=%ROOT%build\QtScrcpy.exe"

if exist "%REL%" (
  start "" "%REL%"
  exit /b 0
)

if exist "%BUILD%" (
  start "" "%BUILD%"
  exit /b 0
)

echo QtScrcpy.exe not found.
echo Expected at:
echo   %REL%
echo   %BUILD%
exit /b 1


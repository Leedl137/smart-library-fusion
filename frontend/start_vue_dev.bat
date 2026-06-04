@echo off
setlocal
cd /d "%~dp0"

set "NODE_DIR=D:\Applications\nodejs"
if exist "%NODE_DIR%\node.exe" (
  set "PATH=%NODE_DIR%;%PATH%"
)

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found in PATH.
  echo Please reopen PowerShell/CMD after installing Node.js, or edit NODE_DIR in this file.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found in PATH.
  pause
  exit /b 1
)

if not exist ".env" copy ".env.example" ".env"
if not exist "node_modules" npm install

npm run dev
endlocal

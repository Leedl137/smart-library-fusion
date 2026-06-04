@echo off
setlocal
cd /d "%~dp0"

set "NODE_DIR=D:\Applications\nodejs"
if exist "%NODE_DIR%\node.exe" (
  set "PATH=%NODE_DIR%;%PATH%"
)

if not exist ".env" copy ".env.example" ".env"
if not exist "node_modules" npm install
npm run build
pause
endlocal
